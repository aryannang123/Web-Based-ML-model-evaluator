import secrets
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy.exc import IntegrityError
from database.db import db
from models.user import User
from models.user_session import UserSession
from routes.auth_utils import get_authenticated_user, revoke_current_session


auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

@auth_bp.route("/register", methods=["POST"])
def register():
    """Register a new user - GitHub Issue #4."""
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "Valid JSON is required"}), 400

    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if not all(isinstance(x, str) for x in (username, email, password)):
        return jsonify({"error": "All fields are required"}), 400

    username = username.strip()
    email = email.strip().lower()

    if not username or not email or not password:
        return jsonify({"error": "All fields are required"}), 400

    if len(username) > 80:
        return jsonify({"error": "Username is too long"}), 400

    if (len(email) > 120 or " " in email
            or email.count("@") != 1
            or not email.split("@")[0]
            or "." not in email.split("@")[1]
            or not email.split("@")[1].strip(".")):
        return jsonify({"error": "Invalid email address"}), 400

    if not 8 <= len(password) <= 128:
        return jsonify({"error": "Password must be 8 to 128 characters"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 409

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already exists"}), 409

    user = User(
        username=username,
        email=email,
        password_hash=generate_password_hash(password)
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

    return jsonify({
        "message": "Registration successful",
        "user_id": user.id
    }), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Valid JSON is required"}), 400

    username = data.get("username")
    password = data.get("password")
    if not isinstance(username, str) or not isinstance(password, str):
        return jsonify({"error": "Username and password are required"}), 400

    username = username.strip()
    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400
    if len(username) > 80 or len(password) > 128:
        return jsonify({"error": "Invalid username or password"}), 401

    user = User.query.filter_by(username=username).first()
    if user is None or not check_password_hash(user.password_hash, password):
        return jsonify({"error": "Invalid username or password"}), 401

    # Revoke any old browser session before issuing a fresh server-tracked one.
    revoke_current_session()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    auth_session = UserSession(
        session_id=secrets.token_urlsafe(32),
        user_id=user.id,
        last_seen_at=now,
    )
    try:
        db.session.add(auth_session)
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Unable to establish session"}), 500

    session.clear()
    session.permanent = True
    session["session_id"] = auth_session.session_id
    session["user_id"] = user.id
    session["username"] = user.username

    return jsonify({
        "message": "Login successful",
        "user": {"id": user.id, "username": user.username},
        "redirect_url": "/",
    }), 200


@auth_bp.route("/session", methods=["GET"])
def current_session():
    user = get_authenticated_user()
    if user is None:
        return jsonify({"authenticated": False}), 200

    return jsonify({
        "authenticated": True,
        "user": {"id": user.id, "username": user.username},
    }), 200

@auth_bp.route("/logout", methods=["POST"])
def logout():
    """Revoke the current server-side session and expire the browser cookie."""
    was_active = revoke_current_session()
    if was_active:
        return jsonify({
            "message": "Logout successful",
            "redirect_url": "/login",
        }), 200
    return jsonify({
        "message": "No active session to log out",
        "redirect_url": "/login",
    }), 200
