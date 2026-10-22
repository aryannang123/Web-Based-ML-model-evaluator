"""Read-only access to model runs explicitly shared for Instructor review."""

from flask import Blueprint, jsonify

from models.model import MLModel
from routes.auth_utils import roles_required


instructor_bp = Blueprint("instructor", __name__, url_prefix="/api/instructor")


def _result_payload(run):
    evaluation = run.evaluations[-1] if run.evaluations else None
    dataset = run.dataset
    return {
        "id": run.id,
        "model_name": run.model_name,
        "algorithm": run.algorithm,
        "task_type": run.task_type,
        "target_column": run.target_column,
        "status": run.status,
        "dataset": {
            "filename": (run.config_json or {}).get("dataset_name", dataset.filename),
            "row_count": dataset.row_count,
            "column_count": dataset.column_count,
        } if dataset else None,
        "owner_username": run.user.username,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "metrics": evaluation.metrics_json if evaluation else None,
        "confusion_matrix": evaluation.confusion_matrix_json if evaluation else None,
        "visualization": evaluation.visualization_json if evaluation else None,
        "report": evaluation.report_json if evaluation else None,
    }


@instructor_bp.route("/results", methods=["GET"])
@roles_required("instructor")
def list_shared_results():
    runs = MLModel.query.filter_by(
        status="completed", is_shared_with_instructors=True
    ).order_by(MLModel.created_at.desc()).limit(500).all()
    return jsonify({"results": [_result_payload(run) for run in runs]}), 200


@instructor_bp.route("/results/<int:run_id>", methods=["GET"])
@roles_required("instructor")
def get_shared_result(run_id):
    run = MLModel.query.filter_by(
        id=run_id, status="completed", is_shared_with_instructors=True
    ).first()
    if run is None:
        return jsonify({"error": "Result not found"}), 404
    return jsonify({"result": _result_payload(run)}), 200
