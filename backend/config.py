import os
import secrets

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Use a fresh development key when one is not configured. Deployments should
    # provide a stable SECRET_KEY through the environment.
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get(
        "SESSION_COOKIE_SECURE", "false"
    ).lower() == "true"
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'ml_evaluator.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    SAVED_MODELS_FOLDER = os.path.join(BASE_DIR, "saved_models")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max dataset size
    ALLOWED_EXTENSIONS = {"csv"}
