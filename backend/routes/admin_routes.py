"""Administrative account, dataset and read-only activity-log endpoints."""

from flask import Blueprint, jsonify, request

from database.db import db
from models.dataset import Dataset
from models.security import AuditEvent
from models.user import User
from routes.auth_utils import audit_event, current_user, roles_required


admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")
ALLOWED_ROLES = {"student", "instructor", "admin"}


@admin_bp.route("/users", methods=["GET"])
@roles_required("admin")
def list_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return jsonify({"users": [{
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    } for user in users]}), 200


@admin_bp.route("/users/<int:user_id>", methods=["PATCH"])
@roles_required("admin")
def update_user(user_id):
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not data:
        return jsonify({"error": "Provide role and/or is_active as JSON."}), 400
    user = db.session.get(User, user_id)
    if user is None:
        return jsonify({"error": "User not found"}), 404

    new_role = data.get("role", user.role)
    active = data.get("is_active", user.is_active)
    if new_role not in ALLOWED_ROLES or not isinstance(active, bool):
        return jsonify({"error": "Invalid role or account status."}), 400
    actor = current_user()
    if actor.id == user.id and (not active or new_role != "admin"):
        return jsonify({"error": "You cannot remove your own admin access."}), 400
    if user.role == "admin" and (not active or new_role != "admin"):
        other_admins = User.query.filter(
            User.role == "admin", User.is_active.is_(True), User.id != user.id
        ).count()
        if other_admins == 0:
            return jsonify({"error": "At least one active Admin must remain."}), 409

    user.role = new_role
    user.is_active = active
    db.session.commit()
    audit_event(
        "admin.user_updated", actor_user_id=actor.id,
        target_type="user", target_id=user.id,
        details={"role": new_role, "is_active": active},
    )
    return jsonify({"message": "User updated", "user": {
        "id": user.id, "username": user.username,
        "role": user.role, "is_active": user.is_active,
    }}), 200


@admin_bp.route("/datasets", methods=["GET"])
@roles_required("admin")
def list_all_datasets():
    include_archived = request.args.get("include_archived", "false").lower() == "true"
    query = Dataset.query
    if not include_archived:
        query = query.filter_by(is_archived=False)
    datasets = query.order_by(Dataset.created_at.desc()).limit(500).all()
    return jsonify({"datasets": [{
        "id": item.id,
        "owner_id": item.user_id,
        "owner_username": item.user.username,
        "filename": item.filename,
        "file_size": item.file_size,
        "row_count": item.row_count,
        "column_count": item.column_count,
        "is_archived": item.is_archived,
        "metadata": item.metadata_json or {},
        "created_at": item.created_at.isoformat() if item.created_at else None,
    } for item in datasets]}), 200


@admin_bp.route("/datasets/<int:dataset_id>", methods=["PATCH"])
@roles_required("admin")
def archive_dataset(dataset_id):
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get("is_archived"), bool):
        return jsonify({"error": "is_archived must be a boolean."}), 400
    dataset = db.session.get(Dataset, dataset_id)
    if dataset is None:
        return jsonify({"error": "Dataset not found"}), 404
    dataset.is_archived = data["is_archived"]
    db.session.commit()
    actor = current_user()
    audit_event(
        "admin.dataset_archived" if dataset.is_archived else "admin.dataset_restored",
        actor_user_id=actor.id, target_type="dataset", target_id=dataset.id,
        details={"owner_id": dataset.user_id},
    )
    return jsonify({"message": "Dataset status updated",
                    "is_archived": dataset.is_archived}), 200


@admin_bp.route("/logs", methods=["GET"])
@roles_required("admin")
def list_logs():
    try:
        limit = min(max(int(request.args.get("limit", 100)), 1), 200)
        before_id = int(request.args["before_id"]) if "before_id" in request.args else None
    except ValueError:
        return jsonify({"error": "Invalid log pagination values."}), 400
    query = AuditEvent.query
    if before_id is not None:
        query = query.filter(AuditEvent.id < before_id)
    events = query.order_by(AuditEvent.id.desc()).limit(limit).all()
    return jsonify({"events": [{
        "id": event.id,
        "actor_user_id": event.actor_user_id,
        "actor_username": event.actor.username if event.actor else None,
        "event_type": event.event_type,
        "target_type": event.target_type,
        "target_id": event.target_id,
        "details": event.details_json or {},
        "created_at": event.created_at.isoformat() if event.created_at else None,
    } for event in events]}), 200
