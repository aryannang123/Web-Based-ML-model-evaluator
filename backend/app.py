import os

import click
from flask import Flask, jsonify, redirect, request, session, url_for
from flask_cors import CORS

from config import Config
from database.db import db, init_db
from routes import admin_bp, auth_bp, dataset_bp, instructor_bp, ml_bp
from routes.auth_utils import current_user


def create_app(config_class=Config):
    app = Flask(__name__, static_folder="../frontend", static_url_path="")
    app.config.from_object(config_class)

    # The frontend served by this Flask app uses same-origin requests. A
    # separate frontend can be allowed explicitly through configuration.
    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": app.config.get("CORS_ALLOWED_ORIGINS", [
                    "http://127.0.0.1:5000", "http://localhost:5000",
                ])
            }
        },
    )

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["SAVED_MODELS_FOLDER"], exist_ok=True)
    init_db(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(dataset_bp)
    app.register_blueprint(ml_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(instructor_bp)

    @app.before_request
    def validate_active_session():
        if session.get("session_id"):
            current_user()

    def home_for_user(user):
        if user.role == "admin":
            return url_for("admin_page")
        if user.role == "instructor":
            return url_for("instructor_page")
        return url_for("index")

    @app.before_request
    def protect_dashboard_file():
        # Keep the dashboard HTML behind the login flow even when requested
        # through Flask's static-file route directly.
        if request.endpoint == "static":
            filename = (request.view_args or {}).get("filename")
            if filename in {"index.html", "admin.html", "instructor.html"}:
                user = current_user()
                if user is None:
                    return redirect(url_for("login_page"))
                expected = {
                    "index.html": "student",
                    "admin.html": "admin",
                    "instructor.html": "instructor",
                }[filename]
                if user.role != expected:
                    return redirect(home_for_user(user))

    @app.route("/")
    def index():
        user = current_user()
        if user is None:
            return redirect(url_for("login_page"))
        if user.role == "admin":
            return redirect(url_for("admin_page"))
        if user.role == "instructor":
            return redirect(url_for("instructor_page"))
        return app.send_static_file("index.html")

    @app.route("/admin")
    def admin_page():
        user = current_user()
        if user is None:
            return redirect(url_for("login_page"))
        if user.role != "admin":
            return redirect(home_for_user(user))
        return app.send_static_file("admin.html")

    @app.route("/instructor")
    def instructor_page():
        user = current_user()
        if user is None:
            return redirect(url_for("login_page"))
        if user.role != "instructor":
            return redirect(home_for_user(user))
        return app.send_static_file("instructor.html")

    @app.route("/login")
    def login_page():
        user = current_user()
        if user:
            return redirect(home_for_user(user))
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

    @app.cli.command("promote-admin")
    @click.argument("username")
    def promote_admin(username):
        """Promote an existing account using trusted local CLI access."""
        from models.user import User
        from routes.auth_utils import audit_event

        user = User.query.filter_by(username=username).first()
        if user is None:
            raise click.ClickException("User not found")
        user.role = "admin"
        db.session.commit()
        audit_event(
            "admin.role_changed", target_type="user", target_id=user.id,
            details={"role": "admin"},
        )
        print(f"Promoted {username} to Admin.")

    @app.errorhandler(413)
    def request_too_large(_error):
        return jsonify({"error": "Upload exceeds the 16 MiB request limit"}), 413

    return app


if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", 5000))
    host = app.config.get("HOST", "127.0.0.1")

    print(
        f"Starting Web-Based ML Model Evaluator backend "
        f"on http://{host}:{port}"
    )

    app.run(host=host, port=port, debug=app.config.get("DEBUG", False))
