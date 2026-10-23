import os

from flask import Flask, jsonify, redirect, request, session, url_for
from flask_cors import CORS

from config import Config
from database.db import db, init_db
from models.user import User
from routes import auth_bp, dataset_bp, ml_bp


def create_app(config_class=Config):
    app = Flask(__name__, static_folder="../frontend", static_url_path="")
    app.config.from_object(config_class)

    # Restrict cross-origin requests to local development origins.
    # The frontend served by this Flask app uses same-origin requests.
    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": [
                    "http://127.0.0.1:5000",
                    "http://localhost:5000",
                ]
            }
        },
    )

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["SAVED_MODELS_FOLDER"], exist_ok=True)
    init_db(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(dataset_bp)
    app.register_blueprint(ml_bp)

    def has_authenticated_user():
        user_id = session.get("user_id")
        if user_id is None:
            return False

        if db.session.get(User, user_id) is None:
            session.clear()
            return False
        return True

    @app.before_request
    def protect_dashboard_file():
        # Keep the dashboard HTML behind the login flow even when requested
        # through Flask's static-file route directly.
        if (
            request.endpoint == "static"
            and (request.view_args or {}).get("filename") == "index.html"
            and not has_authenticated_user()
        ):
            return redirect(url_for("login_page"))

    @app.route("/")
    def index():
        if not has_authenticated_user():
            return redirect(url_for("login_page"))
        return app.send_static_file("index.html")

    @app.route("/login")
    def login_page():
        if has_authenticated_user():
            return redirect(url_for("index"))
        return app.send_static_file("login.html")

    @app.route("/api/health", methods=["GET"])
    def health_check():
        return jsonify(
            {
                "status": "healthy",
                "service": "Web-Based ML Model Evaluator Backend",
                "version": "1.0.0",
            }
        ), 200

    return app


if __name__ == "__main__":
    app = create_app()
    host = app.config["HOST"]
    port = app.config["PORT"]

    print(
        f"Starting Web-Based ML Model Evaluator backend "
        f"on http://{host}:{port}"
    )

    app.run(host=host, port=port, debug=app.config["DEBUG"])
