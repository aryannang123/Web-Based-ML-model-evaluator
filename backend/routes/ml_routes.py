from flask import Blueprint, g, jsonify

from models.evaluation import EvaluationResult
from models.model import MLModel
from routes.auth_utils import (
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
@login_required
def train_model():
    # TODO: US-18: Implement model training. Resolve submitted dataset IDs only
    # through get_owned_dataset(dataset_id, g.current_user.id).
    return jsonify({"message": "Model training endpoint ready for US-18 implementation"}), 501


@ml_bp.route("/evaluate", methods=["POST"])
@login_required
def evaluate_model():
    # TODO: US-19: Implement model evaluation. Resolve model IDs only through
    # get_owned_model(model_id, g.current_user.id).
    return jsonify({"message": "Model evaluation endpoint ready for US-19 implementation"}), 501
