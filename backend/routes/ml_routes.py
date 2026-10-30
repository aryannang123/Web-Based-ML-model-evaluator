import math
import os
from io import BytesIO
from numbers import Real
from uuid import uuid4

import pandas as pd
from flask import Blueprint, current_app, g, jsonify, request, send_file
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
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
    non_instructor_required,
    role_required,
    log_activity,
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
        "shared_with_instructors": bool(result.shared_with_instructors),
        "model_name": result.model.model_name,
        "configuration": result.model.config_json,
    }


def _instructor_evaluation_response(result):
    """Return only the fields required for read-only instructor review."""
    report = result.report_json or {}
    aggregate_keys = {"accuracy", "macro avg", "weighted avg"}
    return {
        "id": result.id,
        "model_id": result.model_id,
        "model_name": result.model.model_name,
        "algorithm": result.model.algorithm,
        "metrics": result.metrics_json,
        "confusion_matrix": result.confusion_matrix_json,
        "confusion_matrix_labels": [key for key in report if key not in aggregate_keys],
        "report": report or None,
        "created_at": result.created_at.isoformat() if result.created_at else None,
        "owner": result.user.username,
    }


@ml_bp.route("/algorithms", methods=["GET"])
@login_required
def get_algorithms():
    return jsonify({
        **ModelTrainer.algorithms_for()
    }), 200


@ml_bp.route("/models", methods=["GET"])
@non_instructor_required
def list_models():
    models = owned_model_query(g.current_user.id).order_by(
        MLModel.created_at.desc(), MLModel.id.desc()
    ).all()
    return jsonify({"models": [_model_response(item) for item in models]}), 200


@ml_bp.route("/models/<int:model_id>", methods=["GET"])
@non_instructor_required
def get_model(model_id):
    model = get_owned_model(model_id, g.current_user.id)
    if model is None:
        return jsonify({"error": "Model not found"}), 404
    return jsonify({"model": _model_response(model)}), 200


@ml_bp.route("/evaluations", methods=["GET"])
@non_instructor_required
def list_evaluations():
    results = owned_evaluation_query(g.current_user.id).order_by(
        EvaluationResult.created_at.desc(), EvaluationResult.id.desc()
    ).all()
    return jsonify({"evaluations": [_evaluation_response(item) for item in results]}), 200


@ml_bp.route("/evaluations/<int:evaluation_id>", methods=["GET"])
@non_instructor_required
def get_evaluation(evaluation_id):
    result = get_owned_evaluation(evaluation_id, g.current_user.id)
    if result is None:
        return jsonify({"error": "Evaluation not found"}), 404
    return jsonify({"evaluation": _evaluation_response(result)}), 200



@ml_bp.route("/compare", methods=["POST"])
@non_instructor_required
def compare_evaluations():
    payload = request.get_json(silent=True) if request.is_json else None
    ids = payload.get("evaluation_ids") if isinstance(payload, dict) else None
    valid_ids = isinstance(ids, list) and 2 <= len(ids) <= 10
    if not valid_ids or any(type(item) is not int for item in ids) or len(set(ids)) != len(ids):
        return jsonify({"error": "Select between 2 and 10 distinct evaluation IDs."}), 400
    results = owned_evaluation_query(g.current_user.id).filter(EvaluationResult.id.in_(ids)).all()
    if len(results) != len(ids):
        return jsonify({"error": "One or more evaluations were not found."}), 404
    tasks = {(item.model.config_json or {}).get("task_type") for item in results}
    if len(tasks) != 1:
        return jsonify({"error": "Only evaluations for the same task type can be compared."}), 400
    return jsonify({"evaluations": [_evaluation_response(item) for item in results]}), 200


def _owned_artifact(model_id):
    model = get_owned_model(model_id, g.current_user.id)
    if model is None:
        return None, None
    folder = os.path.realpath(current_app.config["SAVED_MODELS_FOLDER"])
    path = os.path.realpath(model.model_path or "")
    try:
        safe = os.path.commonpath([folder, path]) == folder
    except ValueError:
        safe = False
    return model, path if safe and os.path.isfile(path) else None


@ml_bp.route("/models/<int:model_id>/download", methods=["GET"])
@non_instructor_required
def download_model(model_id):
    model, path = _owned_artifact(model_id)
    if model is None or path is None:
        return jsonify({"error": "Model artifact not found."}), 404
    return send_file(path, as_attachment=True, download_name=f"model-{model.id}-{model.algorithm}.joblib")


@ml_bp.route("/evaluations/<int:evaluation_id>/report", methods=["GET"])
@non_instructor_required
def download_report(evaluation_id):
    result = get_owned_evaluation(evaluation_id, g.current_user.id)
    if result is None:
        return jsonify({"error": "Evaluation not found."}), 404
    output = BytesIO()
    pdf = canvas.Canvas(output, pagesize=letter)
    width, height = letter
    y = height - 54
    pdf.setTitle(f"Evaluation report {result.id}")
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(48, y, "ML Model Evaluation Report")
    y -= 30
    pdf.setFont("Helvetica", 10)
    lines = [f"Run ID: {result.id}", f"Model: {result.model.model_name}",
             f"Algorithm: {result.model.algorithm}", f"Created: {result.created_at}"]
    lines.extend(f"{key}: {value}" for key, value in (result.model.config_json or {}).items())
    lines.extend(f"{key}: {value}" for key, value in (result.metrics_json or {}).items())
    for line in lines:
        if y < 48:
            pdf.showPage()
            y = height - 48
            pdf.setFont("Helvetica", 10)
        pdf.drawString(48, y, line[:110])
        y -= 17
    pdf.save()
    output.seek(0)
    return send_file(output, mimetype="application/pdf", as_attachment=True,
                     download_name=f"evaluation-{result.id}.pdf")


@ml_bp.route("/evaluations/<int:evaluation_id>/sharing", methods=["PATCH"])
@non_instructor_required
def update_evaluation_sharing(evaluation_id):
    result = get_owned_evaluation(evaluation_id, g.current_user.id)
    if result is None:
        return jsonify({"error": "Evaluation not found."}), 404
    payload = request.get_json(silent=True) if request.is_json else None
    if not isinstance(payload, dict) or type(payload.get("shared_with_instructors")) is not bool:
        return jsonify({"error": "shared_with_instructors must be a boolean."}), 400
    result.shared_with_instructors = payload["shared_with_instructors"]
    db.session.commit()
    return jsonify({"evaluation_id": result.id,
                    "shared_with_instructors": result.shared_with_instructors}), 200


@ml_bp.route("/instructor/evaluations", methods=["GET"])
@role_required("instructor")
def instructor_evaluations():
    results = (EvaluationResult.query.join(MLModel).join(Dataset)
               .filter(EvaluationResult.shared_with_instructors.is_(True))
               .order_by(EvaluationResult.created_at.desc(), EvaluationResult.id.desc()).all())
    return jsonify({"evaluations": [
        _instructor_evaluation_response(item) for item in results
    ]}), 200


@ml_bp.route("/instructor/evaluations/<int:evaluation_id>", methods=["GET"])
@role_required("instructor")
def instructor_evaluation(evaluation_id):
    result = (EvaluationResult.query.join(MLModel).join(Dataset)
              .filter(EvaluationResult.id == evaluation_id,
                      EvaluationResult.shared_with_instructors.is_(True)).first())
    if result is None:
        return jsonify({"error": "Evaluation not found."}), 404
    return jsonify({"evaluation": _instructor_evaluation_response(result)}), 200


@ml_bp.route("/instructor/compare", methods=["POST"])
@role_required("instructor")
def compare_shared_evaluations():
    payload = request.get_json(silent=True) if request.is_json else None
    ids = payload.get("evaluation_ids") if isinstance(payload, dict) else None
    valid_ids = isinstance(ids, list) and 2 <= len(ids) <= 10
    if not valid_ids or any(type(item) is not int for item in ids) or len(set(ids)) != len(ids):
        return jsonify({"error": "Select between 2 and 10 distinct evaluation IDs."}), 400
    results = (EvaluationResult.query.join(MLModel).join(Dataset)
               .filter(EvaluationResult.id.in_(ids),
                       EvaluationResult.shared_with_instructors.is_(True)).all())
    if len(results) != len(ids):
        return jsonify({"error": "One or more shared evaluations were not found."}), 404
    tasks = {(item.model.config_json or {}).get("task_type") for item in results}
    if len(tasks) != 1:
        return jsonify({"error": "Only shared evaluations for the same task type can be compared."}), 400
    return jsonify({"evaluations": [
        _instructor_evaluation_response(item) for item in results
    ]}), 200

@ml_bp.route("/train", methods=["POST"])
@non_instructor_required
def train_model():
    """Train a model on an owned dataset (US-18).

    Expected JSON body
    ------------------
    {
        "dataset_id":   <int>   -- required; must be owned by the current user
        "algorithm":    <str>   -- one of ModelTrainer.SUPPORTED_ALGORITHMS
        "task_type":    <str>   -- "classification" or "regression"
        "target_column":<str>   -- column name in the dataset CSV
        "model_name":   <str>   -- optional display name (defaults to algorithm)
        "test_size":    <float> -- train/test split ratio (default 0.2)
        "preprocessing":{...}   -- optional preprocessing config dict
            "missing_values": "none"|"drop"|"mean"|"median"|"mode"|"constant"
            "encoding":       "none"|"label"|"onehot"
            "scaling":        "none"|"minmax"|"standard"
    }

    Returns
    -------
    201 JSON with model record including id and status "completed".
    400 on validation / algorithm / incompatible-config errors.
    404 when dataset_id is not found or not owned by the caller.
    """
    body = request.get_json(silent=True) or {}

    # --- 1. Validate required fields ---
    dataset_id = body.get("dataset_id")
    algorithm = body.get("algorithm")
    task_type = body.get("task_type")
    target_column = body.get("target_column")

    missing_fields = [
        name for name, val in [
            ("dataset_id", dataset_id),
            ("algorithm", algorithm),
            ("task_type", task_type),
            ("target_column", target_column),
        ]
        if val is None or (isinstance(val, str) and not val.strip())
    ]
    if missing_fields:
        return jsonify({
            "error": f"Missing required field(s): {', '.join(missing_fields)}"
        }), 400

    # --- 2. Validate algorithm and task_type early (FR-4.1-IT-2) ---
    algorithm = str(algorithm).strip()
    task_type = str(task_type).strip().lower()
    target_column = str(target_column).strip()
    model_name = str(body.get("model_name") or algorithm).strip()

    if algorithm not in ModelTrainer.SUPPORTED_ALGORITHMS:
        return jsonify({
            "error": (
                f"Unsupported algorithm '{algorithm}'. "
                f"Supported algorithms: {', '.join(ModelTrainer.SUPPORTED_ALGORITHMS)}"
            )
        }), 400

    if task_type not in ("classification", "regression"):
        return jsonify({
            "error": (
                f"Unsupported task_type '{task_type}'. "
                "Accepted values are 'classification' or 'regression'."
            )
        }), 400

    # Check algorithm / task_type compatibility
    if (algorithm, task_type) not in ModelTrainer._ESTIMATOR_MAP:
        return jsonify({
            "error": (
                f"Algorithm '{algorithm}' is not compatible with task type '{task_type}'. "
                "For example, 'logistic_regression' supports classification only and "
                "'linear_regression' supports regression only."
            )
        }), 400

    # --- 3. Resolve dataset ownership (FR-4.2-IT-1 / security) ---
    dataset = get_owned_dataset(dataset_id, g.current_user.id)
    if dataset is None:
        return jsonify({"error": "Dataset not found"}), 404

    # --- 4. Load the CSV ---
    try:
        df = pd.read_csv(dataset.file_path)
    except Exception as exc:
        return jsonify({"error": f"Could not read dataset file: {exc}"}), 400

    if target_column not in df.columns:
        return jsonify({
            "error": f"Target column '{target_column}' does not exist in the dataset."
        }), 400

    # --- 5. Preprocessing (optional) ---
    preproc_config = body.get("preprocessing") or {}
    if not isinstance(preproc_config, dict):
        preproc_config = {}

    # Normalise the preprocessing keys so callers can use either top-level
    # or nested syntax.
    preprocessing_summary = {}
    try:
        df_processed, preprocessing_summary = DataPreprocessor.preprocess(
            df,
            config={
                "missing_values": preproc_config.get("missing_values", "none"),
                "encoding":       preproc_config.get("encoding",       "none"),
                "scaling":        preproc_config.get("scaling",        "none"),
                "fill_value":     preproc_config.get("fill_value",     None),
            },
            target_column=target_column,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    # --- 6. Validate target column still exists after preprocessing ---
    if target_column not in df_processed.columns:
        return jsonify({
            "error": (
                f"Target column '{target_column}' was removed during preprocessing. "
                "Check your encoding configuration."
            )
        }), 400

    # --- 7. Train / test split ---
    test_size = body.get("test_size", 0.2)
    if isinstance(test_size, bool) or not isinstance(test_size, Real):
        return jsonify({"error": "test_size must be a finite number greater than 0 and less than 1."}), 400
    if not (0 < test_size < 1) or not math.isfinite(test_size):
        return jsonify({"error": "test_size must be a finite number greater than 0 and less than 1."}), 400

    X = df_processed.drop(columns=[target_column])
    y = df_processed[target_column]

    try:
        X_train, X_test, y_train, y_test = DataPreprocessor.split(
            X, y, test_size=test_size
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    # --- 8. Create the MLModel record in "training" state ---
    config_snapshot = {
        "algorithm":   algorithm,
        "task_type":   task_type,
        "target_column": target_column,
        "test_size":   test_size,
        "preprocessing": preprocessing_summary,
        "train_rows":  int(len(X_train)),
        "test_rows":   int(len(X_test)),
        "feature_count": int(X.shape[1]),
        "features":    list(X.columns),
    }

    ml_model = MLModel(
        user_id=g.current_user.id,
        dataset_id=dataset.id,
        model_name=model_name,
        algorithm=algorithm,
        status="training",
        config_json=config_snapshot,
    )
    db.session.add(ml_model)
    db.session.commit()

    # --- 9. Train ---
    try:
        trained_model = ModelTrainer.train(
            algorithm_name=algorithm,
            task_type=task_type,
            X_train=X_train,
            y_train=y_train,
        )
    except ValueError as exc:
        ml_model.status = "failed"
        db.session.commit()
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        ml_model.status = "failed"
        db.session.commit()
        return jsonify({"error": f"Training failed unexpectedly: {exc}"}), 500

    # --- 10. Persist the model file ---
    from flask import current_app
    saved_models_folder = current_app.config.get("SAVED_MODELS_FOLDER", "saved_models")
    model_filename = f"model_{ml_model.id}.joblib"
    model_path = os.path.join(saved_models_folder, model_filename)
    try:
        ModelTrainer.save(trained_model, model_path)
    except Exception as exc:
        ml_model.status = "failed"
        db.session.commit()
        return jsonify({"error": f"Could not save model file: {exc}"}), 500

    # --- 11. Mark as completed ---
    ml_model.model_path = model_path
    ml_model.status = "completed"
    db.session.commit()

    log_activity(
        action="model_trained",
        user_id=g.current_user.id,
        details={
            "model_id": ml_model.id,
            "algorithm": algorithm,
            "task_type": task_type,
            "dataset_id": dataset.id,
        },
    )

    return jsonify({
        "message": "Model trained successfully.",
        "model": _model_response(ml_model),
        "split": {
            "requested_test_size": test_size,
            "train_rows": int(len(X_train)),
            "test_rows": int(len(X_test)),
        },
    }), 201


@ml_bp.route("/evaluate", methods=["POST"])
@non_instructor_required
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
