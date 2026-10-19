from flask import Blueprint, request, jsonify, current_app
from database.db import db
from models.dataset import Dataset
from models.evaluation import EvaluationResult
from ml.preprocessor import DataPreprocessor
from ml.trainer import ModelTrainer
from ml.evaluator import ModelEvaluator
import os
import pandas as pd

ml_bp = Blueprint("ml", __name__, url_prefix="/api/ml")

@ml_bp.route("/algorithms", methods=["GET"])
def get_algorithms():
    return jsonify(ModelTrainer.get_supported_algorithms()), 200

@ml_bp.route("/train", methods=["POST"])
def train_and_evaluate():
    data = request.get_json() or {}
    dataset_id = data.get("dataset_id")
    target_column = data.get("target_column")
    algorithm = data.get("algorithm")
    split_ratio = float(data.get("split_ratio", 0.2))
    user_id = int(data.get("user_id", 1))

    if not dataset_id or not target_column or not algorithm:
        return jsonify({"error": "dataset_id, target_column, and algorithm are required"}), 400

    dataset = Dataset.query.get_or_404(dataset_id)
    if not os.path.exists(dataset.file_path):
        return jsonify({"error": "Dataset file not found"}), 404

    df = pd.read_csv(dataset.file_path)

    try:
        prepared = DataPreprocessor.prepare_data(
            df=df, target_col=target_column, test_size=split_ratio
        )
        task_type = prepared["task_type"]

        model = ModelTrainer.train(
            algorithm_name=algorithm,
            task_type=task_type,
            X_train=prepared["X_train"],
            y_train=prepared["y_train"]
        )

        metrics = ModelEvaluator.evaluate(
            model=model,
            X_test=prepared["X_test"],
            y_test=prepared["y_test"],
            task_type=task_type
        )

        model_filename = f"model_user{user_id}_ds{dataset_id}_{algorithm}.joblib"
        model_save_path = os.path.join(current_app.config["SAVED_MODELS_FOLDER"], model_filename)
        ModelTrainer.save_model(model, model_save_path)

        eval_result = EvaluationResult(
            user_id=user_id,
            dataset_id=dataset_id,
            model_name=algorithm,
            task_type=task_type,
            split_ratio=split_ratio,
            model_file_path=model_save_path
        )
        eval_result.set_metrics(metrics)
        db.session.add(eval_result)
        db.session.commit()

        return jsonify({
            "message": "Model trained and evaluated successfully",
            "evaluation": eval_result.to_dict(),
            "feature_names": prepared["feature_names"]
        }), 200

    except Exception as e:
        return jsonify({"error": f"Training failed: {str(e)}"}), 500

@ml_bp.route("/evaluations/<int:user_id>", methods=["GET"])
def get_user_evaluations(user_id):
    evals = EvaluationResult.query.filter_by(user_id=user_id).order_by(EvaluationResult.created_at.desc()).all()
    return jsonify([e.to_dict() for e in evals]), 200
