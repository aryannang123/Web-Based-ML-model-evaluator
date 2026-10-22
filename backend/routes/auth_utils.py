from functools import wraps
import hashlib
import secrets
import time

from flask import current_app, jsonify, session

from database.db import db
from models.security import AuditEvent, UserSession
from models.user import User


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def new_session_id():
    return secrets.token_urlsafe(32)


def audit_event(event_type, *, actor_user_id=None, target_type=None,
                target_id=None, details=None):
    """Persist a security/business event without credential or dataset data."""
    db.session.add(
        AuditEvent(
            actor_user_id=actor_user_id,
            event_type=event_type,
            target_type=target_type,
            target_id=str(target_id) if target_id is not None else None,
            details_json=details or {},
        )
    )
    db.session.commit()


def current_user(*, touch=True):
    user_id = session.get("user_id")
    raw_session_id = session.get("session_id")
    if user_id is None:
        return None
    if not raw_session_id:
        session.clear()
        return None

    record = db.session.get(UserSession, digest(raw_session_id))
    now = int(time.time())
    idle_limit = int(current_app.config["SESSION_IDLE_TIMEOUT_SECONDS"])
    if (
        record is None
        or record.user_id != user_id
        or record.expires_at <= now
        or record.last_activity + idle_limit <= now
    ):
        if record is not None:
            db.session.delete(record)
            db.session.commit()
        session.clear()
        return None

    user = db.session.get(User, user_id)
    if user is None or not user.is_active:
        db.session.delete(record)
        db.session.commit()
        session.clear()
        return None

    if touch and now - record.last_activity >= 60:
        record.last_activity = now
        db.session.commit()
    return user


def login_required(view):
    """Reject API requests that lack a current, revocable user session."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if user is None:
            audit_event("auth.access_denied")
            return jsonify({"error": "Authentication required"}), 401
        return view(*args, **kwargs)

    return wrapped


def roles_required(*roles):
    """Require an authenticated user with one of the listed roles."""
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            user = current_user()
            if user.role not in roles:
                audit_event(
                    "authorization.denied",
                    actor_user_id=user.id,
                    details={"required_roles": list(roles)},
                )
                return jsonify({"error": "Insufficient permissions"}), 403
            return view(*args, **kwargs)
        return wrapped
    return decorator
