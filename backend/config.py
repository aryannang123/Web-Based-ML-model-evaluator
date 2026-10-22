import os
import secrets

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Use a fresh development key when one is not configured. Deployments should
    # provide a stable SECRET_KEY through the environment.
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    HOST = os.environ.get("HOST", "127.0.0.1")
    CORS_ALLOWED_ORIGINS = [
        origin.strip()
        for origin in os.environ.get(
            "CORS_ALLOWED_ORIGINS",
            "http://127.0.0.1:5000,http://localhost:5000",
        ).split(",")
        if origin.strip()
    ]
    MIN_PASSWORD_LENGTH = 8
    MAX_PASSWORD_LENGTH = 128
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get(
        "SESSION_COOKIE_SECURE", "false"
    ).lower() == "true"
    PERMANENT_SESSION_LIFETIME = 12 * 60 * 60
    SESSION_IDLE_TIMEOUT_SECONDS = 30 * 60
    LOGIN_RATE_LIMIT_WINDOW_SECONDS = 15 * 60
    LOGIN_RATE_LIMIT_MAX_FAILURES = 10
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'ml_evaluator.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    SAVED_MODELS_FOLDER = os.path.join(BASE_DIR, "saved_models")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MiB maximum upload request
    ALLOWED_EXTENSIONS = {"csv"}
    DATASET_PREVIEW_ROWS = 10
    TRAIN_TEST_RANDOM_STATE = 42
