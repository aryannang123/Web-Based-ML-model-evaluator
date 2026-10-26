import math
import os
from numbers import Real
from uuid import uuid4

import pandas as pd
from flask import Blueprint, current_app, g, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from database.db import db
from ml.evaluator import ModelEvaluator
from ml.preprocessor import DataPreprocessor
from ml.trainer import ModelTrainer
from models.dataset import Dataset
from models.evaluation import EvaluationResult
from models.model import MLModel
from routes.auth_utils import (
    get_owned_dataset,
    get_owned_evaluation,
    get_owned_model,
    login_required,
    owned_evaluation_query,
    owned_model_query,
)


ml_bp = Blueprint("ml", __name__, url_prefix="/api/ml")


def _model_response(model):
    return {
        "id": model.id,
        "dataset_id": model.dataset_id,
        "model_name": model.model_name,
        "algorithm": model.algorithm,
        "status": model.status,
        "configuration": model.config_json,
        "created_at": model.created_at.isoformat() if model.created_at else None,
    }


def _evaluation_response(result):
    return {
        "id": result.id,
        "model_id": result.model_id,
        "algorithm": result.model.algorithm,
        "metrics": result.metrics_json,
        "confusion_matrix": result.confusion_matrix_json,
        "report": result.report_json,
        "created_at": result.created_at.isoformat() if result.created_at else None,
    }


@ml_bp.route("/algorithms", methods=["GET"])
@login_required
def get_algorithms():
    return jsonify({
        "classification": ["logistic_regression", "decision_tree", "random_forest", "knn"],
        "regression": ["linear_regression", "decision_tree", "random_forest", "knn"]
    }), 200


@ml_bp.route("/models", methods=["GET"])
@login_required
def list_models():
    models = owned_model_query(g.current_user.id).order_by(
        MLModel.created_at.desc(), MLModel.id.desc()
    ).all()
    return jsonify({"models": [_model_response(item) for item in models]}), 200


@ml_bp.route("/models/<int:model_id>", methods=["GET"])
@login_required
def get_model(model_id):
    model = get_owned_model(model_id, g.current_user.id)
    if model is None:
        return jsonify({"error": "Model not found"}), 404
    return jsonify({"model": _model_response(model)}), 200


@ml_bp.route("/evaluations", methods=["GET"])
@login_required
def list_evaluations():
    results = owned_evaluation_query(g.current_user.id).order_by(
        EvaluationResult.created_at.desc(), EvaluationResult.id.desc()
    ).all()
    return jsonify({"evaluations": [_evaluation_response(item) for item in results]}), 200


@ml_bp.route("/evaluations/<int:evaluation_id>", methods=["GET"])
@login_required
def get_evaluation(evaluation_id):
    result = get_owned_evaluation(evaluation_id, g.current_user.id)
    if result is None:
        return jsonify({"error": "Evaluation not found"}), 404
    return jsonify({"evaluation": _evaluation_response(result)}), 200


@ml_bp.route("/train", methods=["POST"])
@ml_bp.route("/evaluate", methods=["POST"])
@login_required
def evaluate_model():
    if not request.is_json:
        return jsonify({"error": "A JSON request body is required."}), 400
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "A valid JSON object is required."}), 400

    dataset_id = payload.get("dataset_id")
    if isinstance(dataset_id, bool) or not isinstance(dataset_id, int):
        return jsonify({"error": "dataset_id must be an integer."}), 400
    dataset = get_owned_dataset(dataset_id, g.current_user.id)
    if dataset is None:
        return jsonify({"error": "Dataset not found"}), 404

    test_size = payload.get("test_size", 0.2)
    if isinstance(test_size, bool) or not isinstance(test_size, Real):
        return jsonify({
            "error": "test_size must be a finite number greater than 0 and less than 1."
        }), 400
    test_size = float(test_size)
    if not math.isfinite(test_size) or not 0 < test_size < 1:
        return jsonify({
            "error": "test_size must be a finite number greater than 0 and less than 1."
        }), 400

    target_column = payload.get("target_column")
    if not isinstance(target_column, str) or not target_column:
        return jsonify({"error": "Choose a target column."}), 400
    algorithm = payload.get("algorithm")
    if not isinstance(algorithm, str):
        return jsonify({"error": "Choose a supported algorithm."}), 400
    task_type = payload.get("task_type")
    if task_type is None:
        task_type = {
            "logistic_regression": "classification",
            "linear_regression": "regression",
        }.get(algorithm)
    if not isinstance(task_type, str) or task_type not in {"classification", "regression"}:
        return jsonify({"error": "Choose a classification or regression task."}), 400

    if algorithm == "logistic_regression" and task_type != "classification":
        return jsonify({"error": "Logistic regression requires a classification target."}), 400
    if algorithm == "linear_regression" and task_type != "regression":
        return jsonify({"error": "Linear regression requires a numeric regression target."}), 400
    try:
        ModelTrainer.create_estimator(algorithm, task_type)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    upload_folder = os.path.realpath(current_app.config["UPLOAD_FOLDER"])
    stored_path = os.path.realpath(dataset.file_path)
    try:
        is_in_upload_folder = os.path.commonpath([upload_folder, stored_path]) == upload_folder
    except ValueError:
        is_in_upload_folder = False
    if not is_in_upload_folder or not os.path.isfile(stored_path):
        return jsonify({"error": "The dataset file is missing or unavailable."}), 404
    try:
        frame = pd.read_csv(stored_path)
    except (OSError, PermissionError):
        return jsonify({"error": "The dataset file could not be read."}), 500
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError, ValueError):
        return jsonify({"error": "The dataset CSV is malformed or unreadable."}), 400

    if target_column not in frame.columns:
        return jsonify({"error": "The selected target column was not found in the dataset."}), 400
    frame = frame.dropna(subset=[target_column]).dropna(axis=1, how="all")
    if target_column not in frame.columns:
        return jsonify({"error": "The selected target column has no usable values."}), 400
    X = frame.drop(columns=[target_column])
    y = frame[target_column]
    if X.shape[1] == 0:
        return jsonify({"error": "At least one feature column is required."}), 400
    if task_type == "regression":
        y = pd.to_numeric(y, errors="coerce")
        usable = y.notna()
        X, y = X.loc[usable], y.loc[usable]
    else:
        y = y.astype(str)
    if len(y) < 2:
        return jsonify({"error": "At least 2 usable samples are required for training and testing."}), 400

    stratify = y if task_type == "classification" else None
    if stratify is not None and y.value_counts().min() < 2:
        return jsonify({
            "error": "Each target class needs at least 2 samples for a stratified split."
        }), 400
    try:
        X_train, X_test, y_train, y_test = DataPreprocessor.split(
            X, y, test_size=test_size, random_state=42, stratify=stratify
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    minimum_train_count = 5 if algorithm == "knn" else 2
    if len(X_train) < minimum_train_count:
        return jsonify({
            "error": (
                f"The selected split leaves {len(X_train)} training samples, but "
                f"{algorithm} requires at least {minimum_train_count}. Choose a different ratio "
                "or provide more data."
            )
        }), 400
    if algorithm == "logistic_regression" and y_train.value_counts().min() < 2:
        return jsonify({
            "error": "Logistic regression needs at least 2 training samples from every target class."
        }), 400

    try:
        fitted_model = ModelTrainer.train(algorithm, task_type, X_train, y_train)
        metrics, confusion, report = ModelEvaluator.evaluate(
            fitted_model, X_test, y_test, task_type
        )
    except (ValueError, TypeError) as exc:
        return jsonify({"error": f"The model could not be trained with this data: {exc}"}), 400

    split_summary = {
        "train_rows": len(X_train),
        "test_rows": len(X_test),
        "train_fraction": len(X_train) / len(X),
        "test_fraction": len(X_test) / len(X),
        "requested_test_size": test_size,
    }
    model_path = None
    try:
        model_folder = os.path.abspath(current_app.config["SAVED_MODELS_FOLDER"])
        os.makedirs(model_folder, exist_ok=True)
        model_path = os.path.join(model_folder, f"{uuid4().hex}.joblib")
        if os.path.commonpath([model_folder, os.path.abspath(model_path)]) != model_folder:
            return jsonify({"error": "Unable to safely save the trained model."}), 500
        ModelTrainer.save(fitted_model, model_path)
        model = MLModel(
            user_id=g.current_user.id,
            dataset_id=dataset.id,
            model_name=f"{algorithm} ({target_column})",
            algorithm=algorithm,
            model_path=model_path,
            status="complete",
            config_json={
                "target_column": target_column,
                "task_type": task_type,
                "test_size": test_size,
                "random_state": 42,
                **split_summary,
            },
        )
        db.session.add(model)
        db.session.flush()
        evaluation = EvaluationResult(
            user_id=g.current_user.id,
            model_id=model.id,
            metrics_json=metrics,
            confusion_matrix_json=confusion,
            report_json=report,
        )
        db.session.add(evaluation)
        db.session.commit()
    except (OSError, SQLAlchemyError):
        db.session.rollback()
        if model_path:
            try:
                os.remove(model_path)
            except FileNotFoundError:
                pass
            except OSError:
                current_app.logger.exception("Failed to remove an incomplete model artifact")
        current_app.logger.exception("Failed to save model evaluation")
        return jsonify({"error": "The model evaluation could not be saved. Please try again."}), 500

    return jsonify({
        "model_id": model.id,
        "evaluation_id": evaluation.id,
        "algorithm": algorithm,
        "task_type": task_type,
        "metrics": metrics,
        "confusion_matrix": confusion,
        "report": report,
        "split": split_summary,
    }), 201
