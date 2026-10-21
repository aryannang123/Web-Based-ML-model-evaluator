from functools import wraps

from flask import jsonify, session

from database.db import db
from models.user import User


def login_required(view):
    """Reject API requests that do not have an authenticated session."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        user_id = session.get("user_id")
        if user_id is None or db.session.get(User, user_id) is None:
            session.clear()
            return jsonify({"error": "Authentication required"}), 401
        return view(*args, **kwargs)

    return wrapped
