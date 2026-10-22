import time

from flask import Blueprint, current_app, jsonify, request, session
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from database.db import db
from models.security import LoginThrottle, UserSession
from models.user import User
from routes.auth_utils import (
    audit_event,
    current_user,
    digest,
    login_required,
    new_session_id,
)


auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def _throttle_key():
    address = request.remote_addr or "unknown"
    secret = current_app.config["SECRET_KEY"]
    return digest(f"{secret}:{address}")


def _login_is_throttled(now):
    key = _throttle_key()
    record = db.session.get(LoginThrottle, key)
    window = int(current_app.config["LOGIN_RATE_LIMIT_WINDOW_SECONDS"])
    if record is None:
        return False
    if record.blocked_until > now:
        return True
    if record.window_started + window <= now:
        db.session.delete(record)
        db.session.commit()
    return False


def _record_failed_login(now):
    key = _throttle_key()
    window = int(current_app.config["LOGIN_RATE_LIMIT_WINDOW_SECONDS"])
    limit = int(current_app.config["LOGIN_RATE_LIMIT_MAX_FAILURES"])
    record = db.session.get(LoginThrottle, key)
    if record is None or record.window_started + window <= now:
        if record is not None:
            db.session.delete(record)
        record = LoginThrottle(
            key_hash=key, window_started=now, failed_count=0, blocked_until=0
        )
        db.session.add(record)
    record.failed_count += 1
    if record.failed_count >= limit:
        record.blocked_until = now + window
    db.session.commit()


@auth_bp.route("/register", methods=["POST"])
def register():
    """Create a student account; elevated roles are assigned by Admin/CLI."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Valid JSON is required"}), 400

    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    if not all(isinstance(value, str) for value in (username, email, password)):
        return jsonify({"error": "All fields are required"}), 400

    username = username.strip()
    email = email.strip().lower()
    if not username or not email or not password:
        return jsonify({"error": "All fields are required"}), 400
    if len(username) > 80:
        return jsonify({"error": "Username is too long"}), 400
    if (
        len(email) > 120
        or " " in email
        or email.count("@") != 1
        or not email.split("@")[0]
        or "." not in email.split("@")[1]
        or not email.split("@")[1].strip(".")
    ):
        return jsonify({"error": "Invalid email address"}), 400
    minimum = int(current_app.config.get("MIN_PASSWORD_LENGTH", 8))
    maximum = int(current_app.config.get("MAX_PASSWORD_LENGTH", 128))
    if len(password) < minimum:
        return jsonify({"error": f"Password must be at least {minimum} characters"}), 400
    if len(password) > maximum:
        return jsonify({"error": f"Password must be at most {maximum} characters"}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 409
    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already exists"}), 409

    user = User(
        username=username,
        email=email,
        password_hash=generate_password_hash(password),
        role="student",
        is_active=True,
    )
    try:
        db.session.add(user)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Account already exists"}), 409
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Registration failed"}), 500

    audit_event("auth.registered", actor_user_id=user.id, target_type="user",
                target_id=user.id)
    return jsonify({"message": "Registration successful", "user_id": user.id}), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Valid JSON is required"}), 400

    username = data.get("username")
    password = data.get("password")
    if not isinstance(username, str) or not isinstance(password, str):
        return jsonify({"error": "Username and password are required"}), 400
    maximum = int(current_app.config.get("MAX_PASSWORD_LENGTH", 128))
    if len(username) > 80 or len(password) > maximum:
        return jsonify({"error": "Invalid username or password"}), 401
    username = username.strip()
    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    now = int(time.time())
    if _login_is_throttled(now):
        audit_event("auth.login_throttled")
        return jsonify({"error": "Too many attempts. Try again later."}), 429

    user = User.query.filter_by(username=username).first()
    if (
        user is None
        or not user.is_active
        or not check_password_hash(user.password_hash, password)
    ):
        _record_failed_login(now)
        audit_event("auth.login_failed")
        return jsonify({"error": "Invalid username or password"}), 401

    throttle = db.session.get(LoginThrottle, _throttle_key())
    if throttle is not None:
        db.session.delete(throttle)

    raw_session_id = new_session_id()
    max_lifetime = int(current_app.permanent_session_lifetime.total_seconds())
    db.session.add(
        UserSession(
            token_hash=digest(raw_session_id),
            user_id=user.id,
            created_at=now,
            last_activity=now,
            expires_at=now + max_lifetime,
        )
    )
    db.session.commit()

    session.clear()
    session.permanent = True
    session["user_id"] = user.id
    session["username"] = user.username
    session["session_id"] = raw_session_id
    audit_event("auth.login_succeeded", actor_user_id=user.id,
                target_type="user", target_id=user.id)
    return jsonify({
        "message": "Login successful",
        "user": {"id": user.id, "username": user.username, "role": user.role},
        "redirect_url": (
            "/admin" if user.role == "admin" else
            "/instructor" if user.role == "instructor" else "/"
        ),
    }), 200


@auth_bp.route("/session", methods=["GET"])
def current_session():
    user = current_user()
    if user is None:
        return jsonify({"authenticated": False}), 200
    return jsonify({
        "authenticated": True,
        "user": {"id": user.id, "username": user.username, "role": user.role},
    }), 200


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    user = current_user()
    raw_session_id = session.get("session_id")
    record = db.session.get(UserSession, digest(raw_session_id))
    if record is not None:
        db.session.delete(record)
        db.session.commit()
    session.clear()
    audit_event("auth.logout", actor_user_id=user.id, target_type="user",
                target_id=user.id)
    return jsonify({"message": "Logout successful"}), 200
