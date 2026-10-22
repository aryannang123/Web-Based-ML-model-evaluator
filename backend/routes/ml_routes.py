"""Owner-scoped ML configuration, training, comparison and export APIs."""

from datetime import datetime, timezone
from io import BytesIO
import json
import os
from uuid import uuid4

import pandas as pd
from flask import Blueprint, current_app, jsonify, request, send_file

from database.db import db
from ml.evaluator import ModelEvaluator
from ml.preprocessor import DataPreprocessor
from ml.trainer import ModelTrainer
from models.dataset import Dataset
from models.evaluation import EvaluationResult
from models.model import MLModel
from routes.auth_utils import audit_event, current_user, roles_required


ml_bp = Blueprint("ml", __name__, url_prefix="/api/ml")


def _owned_dataset(dataset_id, user_id):
    return Dataset.query.filter_by(
        id=dataset_id, user_id=user_id, is_archived=False
    ).first()


def _owned_run(run_id, user_id):
    return MLModel.query.filter_by(id=run_id, user_id=user_id).first()


def _result_payload(run):
    evaluation = run.evaluations[-1] if run.evaluations else None
    return {
        "id": run.id,
        "model_name": run.model_name,
        "dataset_id": run.dataset_id,
        "dataset_name": (run.config_json or {}).get(
            "dataset_name", run.dataset.filename if run.dataset else None
        ),
        "dataset_version": (run.config_json or {}).get("dataset_version"),
        "algorithm": run.algorithm,
        "task_type": run.task_type,
        "target_column": run.target_column,
        "status": run.status,
        "configuration": run.config_json or {},
        "is_shared_with_instructors": run.is_shared_with_instructors,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "metrics": evaluation.metrics_json if evaluation else None,
        "confusion_matrix": evaluation.confusion_matrix_json if evaluation else None,
        "visualization": evaluation.visualization_json if evaluation else None,
        "report": evaluation.report_json if evaluation else None,
    }


@ml_bp.route("/algorithms", methods=["GET"])
@roles_required("student", "admin")
def get_algorithms():
    return jsonify({"classification": ModelTrainer.SUPPORTED_ALGORITHMS[
        "classification"], "regression": ModelTrainer.SUPPORTED_ALGORITHMS[
        "regression"]}), 200


@ml_bp.route("/runs", methods=["GET"])
@roles_required("student", "admin")
def list_runs():
    user = current_user()
    runs = MLModel.query.filter_by(user_id=user.id).order_by(
        MLModel.created_at.desc()
    ).limit(200).all()
    return jsonify({"runs": [_result_payload(run) for run in runs]}), 200


@ml_bp.route("/runs/<int:run_id>", methods=["GET"])
@roles_required("student", "admin")
def get_run(run_id):
    user = current_user()
    run = _owned_run(run_id, user.id)
    if run is None:
        return jsonify({"error": "Run not found"}), 404
    return jsonify({"run": _result_payload(run)}), 200


@ml_bp.route("/train", methods=["POST"])
@roles_required("student", "admin")
def train_model():
    user = current_user()
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Valid JSON is required"}), 400
    try:
        dataset_id = int(data.get("dataset_id"))
        target_column = data.get("target_column")
        algorithm = data.get("algorithm")
        test_size = float(data.get("test_size", 0.2))
        share = data.get("share_with_instructors", False)
        model_name = str(data.get("model_name") or "").strip()
        if not isinstance(share, bool):
            raise ValueError("Share setting must be a boolean.")
        if not 0.1 <= test_size <= 0.5:
            raise ValueError("Test split must be between 10% and 50%.")
        if not isinstance(algorithm, str):
            raise ValueError("Select a supported algorithm.")
        if not isinstance(target_column, str) or not target_column:
            raise ValueError("Select a target column.")
        dataset = _owned_dataset(dataset_id, user.id)
        if dataset is None:
            return jsonify({"error": "Dataset not found"}), 404
        if target_column is None:
            target_column = dataset.target_column
        frame = pd.read_csv(dataset.file_path, encoding="utf-8-sig")
        if target_column not in frame.columns:
            raise ValueError("The selected target is not in this dataset.")
        frame = frame.dropna(subset=[target_column])
        if len(frame) < 4:
            raise ValueError("At least four rows with target values are required.")
        target = DataPreprocessor.validate_target(frame, target_column)
        task_type = DataPreprocessor.infer_task_type(target)
        if algorithm not in ModelTrainer.SUPPORTED_ALGORITHMS[task_type]:
            raise ValueError(
                f"{algorithm.replace('_', ' ').title()} is not supported for {task_type}."
            )
        X = frame.drop(columns=[target_column])
        y = target
        preprocessing = dataset.preprocessing_json or {
            "missing_strategy": "impute",
            "numeric_imputer": "median",
            "encode_categorical": True,
            "scale_numeric": True,
        }
        if preprocessing.get("missing_strategy") == "drop_rows":
            complete_rows = X.notna().all(axis=1)
            X = X.loc[complete_rows]
            y = y.loc[complete_rows]
        if X.shape[1] < 1:
            raise ValueError("The dataset needs at least one feature column.")
        X_train, X_test, y_train, y_test = DataPreprocessor.split(
            X, y, test_size=test_size,
            random_state=current_app.config["TRAIN_TEST_RANDOM_STATE"],
            task_type=task_type,
        )
        if len(X_train) < 2 or len(X_test) < 2:
            raise ValueError(
                "This split needs at least two training and two test rows; "
                "choose a larger test percentage or upload more data."
            )
    except (TypeError, ValueError, KeyError, pd.errors.ParserError) as error:
        return jsonify({"error": str(error)}), 400
    except Exception:
        current_app.logger.exception("Could not prepare the requested training run")
        return jsonify({"error": "Training configuration could not be prepared."}), 400

    name = model_name[:128] or f"{algorithm.replace('_', ' ').title()} run"
    config = {
        "dataset_sha256": (dataset.metadata_json or {}).get("sha256"),
        "dataset_name": dataset.filename,
        "dataset_version": dataset.versions[-1].version_number if dataset.versions else 1,
        "dataset_rows": int(len(frame)),
        "target_column": target_column,
        "algorithm": algorithm,
        "task_type": task_type,
        "test_size": test_size,
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "random_state": int(current_app.config["TRAIN_TEST_RANDOM_STATE"]),
        "preprocessing": preprocessing,
    }
    dataset_version_id = dataset.versions[-1].id if dataset.versions else None
    run = MLModel(
        user_id=user.id, dataset_id=dataset.id,
        dataset_version_id=dataset_version_id, model_name=name,
        algorithm=algorithm, status="running", config_json=config,
        task_type=task_type, target_column=target_column,
        test_size=test_size, is_shared_with_instructors=share,
    )
    db.session.add(run)
    db.session.commit()
    run_id = run.id

    model_path = os.path.join(
        current_app.config["SAVED_MODELS_FOLDER"],
        f"run-{run_id}-{uuid4().hex}.joblib",
    )
    try:
        estimator = ModelTrainer.train(
            algorithm, task_type, X_train, y_train,
            random_state=current_app.config["TRAIN_TEST_RANDOM_STATE"],
            preprocessing=preprocessing,
        )
        evaluation = ModelEvaluator.evaluate(estimator, X_test, y_test, task_type)
        ModelTrainer.save(estimator, model_path)
        run.model_path = model_path
        run.status = "completed"
        db.session.add(EvaluationResult(
            user_id=user.id,
            model_id=run.id,
            metrics_json=evaluation["metrics"],
            confusion_matrix_json=evaluation["confusion_matrix"],
            visualization_json=evaluation["visualization"],
            report_json={
                "classes": evaluation["classes"],
                "dataset": dataset.filename,
                "configuration": config,
            },
        ))
        db.session.commit()
        audit_event("model.training_completed", actor_user_id=user.id,
                    target_type="model_run", target_id=run.id,
                    details={"algorithm": algorithm, "task_type": task_type})
        return jsonify({"run": _result_payload(run)}), 201
    except Exception:
        db.session.rollback()
        run = db.session.get(MLModel, run_id)
        if run is not None:
            run.status = "failed"
            run.model_path = None
            db.session.commit()
        if os.path.exists(model_path):
            os.remove(model_path)
        current_app.logger.exception("Model training failed for run %s", run_id)
        audit_event("model.training_failed", actor_user_id=user.id,
                    target_type="model_run", target_id=run_id)
        return jsonify({"error": "Training failed. Check the target and data, then retry."}), 422


@ml_bp.route("/compare", methods=["POST"])
@roles_required("student", "admin")
def compare_runs():
    user = current_user()
    data = request.get_json(silent=True)
    run_ids = data.get("run_ids") if isinstance(data, dict) else None
    if (
        not isinstance(run_ids, list)
        or not 2 <= len(run_ids) <= 10
        or any(not isinstance(value, int) or isinstance(value, bool) for value in run_ids)
        or len(set(run_ids)) != len(run_ids)
    ):
        return jsonify({"error": "Select between two and ten distinct completed runs."}), 400
    runs = MLModel.query.filter(
        MLModel.user_id == user.id,
        MLModel.id.in_(run_ids),
        MLModel.status == "completed",
    ).all()
    if len(runs) != len(run_ids):
        return jsonify({"error": "One or more runs are unavailable."}), 404
    if len({(run.dataset_id, run.task_type) for run in runs}) != 1:
        return jsonify({"error": "Runs must use the same dataset and task type."}), 400
    return jsonify({"runs": [_result_payload(run) for run in runs]}), 200


@ml_bp.route("/runs/<int:run_id>/share", methods=["PATCH"])
@roles_required("student", "admin")
def set_instructor_sharing(run_id):
    user = current_user()
    run = _owned_run(run_id, user.id)
    if run is None:
        return jsonify({"error": "Run not found"}), 404
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get("shared"), bool):
        return jsonify({"error": "shared must be a boolean."}), 400
    if run.status != "completed":
        return jsonify({"error": "Only completed runs can be shared."}), 409
    run.is_shared_with_instructors = data["shared"]
    db.session.commit()
    audit_event("model.instructor_sharing_changed", actor_user_id=user.id,
                target_type="model_run", target_id=run.id,
                details={"shared": run.is_shared_with_instructors})
    return jsonify({"shared": run.is_shared_with_instructors}), 200


@ml_bp.route("/runs/<int:run_id>/download/model", methods=["GET"])
@roles_required("student", "admin")
def download_model(run_id):
    user = current_user()
    run = _owned_run(run_id, user.id)
    if run is None or run.status != "completed" or not run.model_path:
        return jsonify({"error": "Model artifact not found"}), 404
    root = os.path.realpath(current_app.config["SAVED_MODELS_FOLDER"])
    path = os.path.realpath(run.model_path)
    if os.path.commonpath([root, path]) != root or not os.path.isfile(path):
        return jsonify({"error": "Model artifact not found"}), 404
    return send_file(path, as_attachment=True, download_name=f"model-run-{run.id}.joblib")


@ml_bp.route("/runs/<int:run_id>/download/report", methods=["GET"])
@roles_required("student", "admin")
def download_report(run_id):
    user = current_user()
    run = _owned_run(run_id, user.id)
    if run is None or run.status != "completed" or not run.evaluations:
        return jsonify({"error": "Evaluation report not found"}), 404
    evaluation = run.evaluations[-1]
    payload = {
        "run": _result_payload(run),
        "metrics": evaluation.metrics_json,
        "confusion_matrix": evaluation.confusion_matrix_json,
        "report": evaluation.report_json,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    stream = BytesIO(json.dumps(payload, indent=2, allow_nan=False).encode("utf-8"))
    stream.seek(0)
    return send_file(stream, mimetype="application/json", as_attachment=True,
                     download_name=f"evaluation-run-{run.id}.json")


@ml_bp.route("/evaluate", methods=["POST"])
@roles_required("student", "admin")
def evaluate_model():
    user = current_user()
    data = request.get_json(silent=True)
    run_id = data.get("run_id") if isinstance(data, dict) else None
    if not isinstance(run_id, int) or isinstance(run_id, bool):
        return jsonify({"error": "A valid run_id is required."}), 400
    run = _owned_run(run_id, user.id)
    if run is None or run.status != "completed":
        return jsonify({"error": "Run results are unavailable."}), 404
    return jsonify({"run": _result_payload(run)}), 200
