import os
from flask import Blueprint, jsonify, request, g
from database.db import db
from models.user import User
from models.dataset import Dataset
from models.activity_log import ActivityLog
from routes.auth_utils import admin_required, log_activity

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


# ─── 1. USER ACCOUNT MANAGEMENT (FR-7.1 / UC-09 / SEC-AZ-3) ──────────────────

@admin_bp.route("/users", methods=["GET"])
@admin_required
def list_users():
    """Admin view of all registered accounts and their status."""
    users = User.query.order_by(User.id).all()
    log_activity(
        "ADMIN_VIEW_USERS",
        user_id=g.current_user.id,
        details=f"Admin {g.current_user.username} viewed registered users list ({len(users)} users)",
        ip_address=request.remote_addr
    )
    return jsonify({
        "users": [u.to_dict() for u in users],
        "total": len(users)
    }), 200


@admin_bp.route("/users/<int:user_id>", methods=["GET"])
@admin_required
def get_user_details(user_id):
    """Admin inspects a specific user account."""
    user = db.session.get(User, user_id)
    if user is None:
        return jsonify({"error": "User not found"}), 404

    return jsonify({"user": user.to_dict()}), 200


@admin_bp.route("/users/<int:user_id>", methods=["PATCH"])
@admin_required
def manage_user_account(user_id):
    """Admin performs supported account management actions (e.g., deactivate or activate)."""
    user = db.session.get(User, user_id)
    if user is None:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Valid JSON is required"}), 400

    changed = False

    # Deactivate / activate action
    if "is_active" in data:
        is_active = data["is_active"]
        if not isinstance(is_active, bool):
            return jsonify({"error": "is_active must be a boolean"}), 400

        # Safety check: Prevent admin from locking out their own account
        if user.id == g.current_user.id and not is_active:
            return jsonify({"error": "Cannot deactivate your own administrator account"}), 400

        user.is_active = is_active
        changed = True

    # Role adjustment
    if "role" in data:
        new_role = data["role"]
        if new_role not in ("student", "instructor", "admin"):
            return jsonify({"error": "Invalid role. Must be 'student', 'instructor', or 'admin'"}), 400

        if user.id == g.current_user.id and new_role != "admin":
            return jsonify({"error": "Cannot demote your own administrator role"}), 400

        user.role = new_role
        changed = True

    if not changed:
        return jsonify({"error": "No valid management action specified (supported: is_active, role)"}), 400

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Failed to update user account"}), 500

    log_activity(
        "ADMIN_ACCOUNT_MANAGEMENT",
        user_id=g.current_user.id,
        details=f"Admin {g.current_user.username} modified user #{user.id} ({user.username}): active={user.is_active}, role={user.role}",
        ip_address=request.remote_addr
    )

    return jsonify({
        "message": "User account updated successfully",
        "user": user.to_dict()
    }), 200


# ─── 2. DATASET OVERSIGHT (FR-7.2 / UC-13 / SEC-AZ-4) ─────────────────────────

@admin_bp.route("/datasets", methods=["GET"])
@admin_required
def list_all_datasets():
    """Admin views stored dataset records across all users with metadata."""
    datasets = Dataset.query.order_by(Dataset.created_at.desc()).all()
    log_activity(
        "ADMIN_VIEW_DATASETS",
        user_id=g.current_user.id,
        details=f"Admin {g.current_user.username} viewed dataset oversight list ({len(datasets)} datasets)",
        ip_address=request.remote_addr
    )
    return jsonify({
        "datasets": [
            {
                "id": d.id,
                "user_id": d.user_id,
                "owner_username": d.user.username if d.user else "unknown",
                "filename": d.filename,
                "row_count": d.row_count,
                "column_count": d.column_count,
                "metadata": d.metadata_json or {},
                "dataset_metadata": d.metadata_json or {},
                "created_at": d.created_at.isoformat() if d.created_at else None
            }
            for d in datasets
        ],
        "total": len(datasets)
    }), 200


@admin_bp.route("/datasets/<int:dataset_id>", methods=["GET"])
@admin_required
def get_dataset_details(dataset_id):
    """Admin inspects a specific dataset record and its metadata."""
    dataset = db.session.get(Dataset, dataset_id)
    if dataset is None:
        return jsonify({"error": "Dataset not found"}), 404

    return jsonify({
        "dataset": {
            "id": dataset.id,
            "user_id": dataset.user_id,
            "owner_username": dataset.user.username if dataset.user else "unknown",
            "filename": dataset.filename,
            "row_count": dataset.row_count,
            "column_count": dataset.column_count,
            "metadata": dataset.metadata_json or {},
            "dataset_metadata": dataset.metadata_json or {},
            "created_at": dataset.created_at.isoformat() if dataset.created_at else None
        }
    }), 200


@admin_bp.route("/datasets/<int:dataset_id>", methods=["DELETE"])
@admin_required
def delete_dataset_record(dataset_id):
    """Admin performs supported dataset management operation (deleting invalid/stale data)."""
    dataset = db.session.get(Dataset, dataset_id)
    if dataset is None:
        return jsonify({"error": "Dataset not found"}), 404

    file_path = dataset.file_path
    owner_username = dataset.user.username if dataset.user else "unknown"
    dataset_name = dataset.filename

    try:
        db.session.delete(dataset)
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Failed to remove dataset record"}), 500

    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except OSError:
            pass

    log_activity(
        "ADMIN_DATASET_DELETE",
        user_id=g.current_user.id,
        details=f"Admin {g.current_user.username} deleted dataset #{dataset_id} ('{dataset_name}' owned by {owner_username})",
        ip_address=request.remote_addr
    )

    return jsonify({
        "message": f"Dataset '{dataset_name}' deleted successfully by administrator"
    }), 200


# ─── 3. SYSTEM ACTIVITY LOGS (FR-7.3 / UC-14 / SEC-AZ-6 / SEC-AUD-1) ──────────

@admin_bp.route("/logs", methods=["GET"])
@admin_required
def get_activity_logs():
    """Admin views system activity logs in read-only mode."""
    logs = ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(200).all()
    return jsonify({
        "logs": [l.to_dict() for l in logs],
        "total": len(logs)
    }), 200
