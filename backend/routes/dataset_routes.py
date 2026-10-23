from flask import Blueprint, g, jsonify

from models.dataset import Dataset

from routes.auth_utils import get_owned_dataset, login_required, owned_dataset_query


dataset_bp = Blueprint("dataset", __name__, url_prefix="/api/dataset")


def _dataset_response(dataset):
    """Return owner-visible metadata without exposing a server filesystem path."""
    return {
        "id": dataset.id,
        "filename": dataset.filename,
        "file_size": dataset.file_size,
        "row_count": dataset.row_count,
        "column_count": dataset.column_count,
        "metadata": dataset.metadata_json,
        "created_at": dataset.created_at.isoformat() if dataset.created_at else None,
    }


@dataset_bp.route("", methods=["GET"])
@login_required
def list_datasets():
    datasets = owned_dataset_query(g.current_user.id).order_by(
        Dataset.created_at.asc(), Dataset.id.asc()
    ).all()
    return jsonify({"datasets": [_dataset_response(item) for item in datasets]}), 200


@dataset_bp.route("/<int:dataset_id>", methods=["GET"])
@login_required
def get_dataset(dataset_id):
    dataset = get_owned_dataset(dataset_id, g.current_user.id)
    if dataset is None:
        return jsonify({"error": "Dataset not found"}), 404
    return jsonify({"dataset": _dataset_response(dataset)}), 200


@dataset_bp.route("/upload", methods=["POST"])
@login_required
def upload_dataset():
    # TODO: US-08: Implement CSV dataset upload. When implemented, set user_id
    # exclusively from g.current_user.id; never accept an owner ID from the client.
    return jsonify({"message": "Dataset upload endpoint ready for US-08 implementation"}), 501


@dataset_bp.route("/<int:dataset_id>/preview", methods=["GET"])
@login_required
def preview_dataset(dataset_id):
    if get_owned_dataset(dataset_id, g.current_user.id) is None:
        return jsonify({"error": "Dataset not found"}), 404
    # TODO: US-12: Display dataset preview.
    return jsonify({"message": "Dataset preview endpoint ready for US-12 implementation"}), 501


@dataset_bp.route("/<int:dataset_id>/statistics", methods=["GET"])
@login_required
def dataset_statistics(dataset_id):
    if get_owned_dataset(dataset_id, g.current_user.id) is None:
        return jsonify({"error": "Dataset not found"}), 404
    # TODO: US-13: Display dataset statistics.
    return jsonify({"message": "Dataset statistics endpoint ready for US-13 implementation"}), 501
