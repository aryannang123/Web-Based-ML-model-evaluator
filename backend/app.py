
import os
from flask import Flask, jsonify
from flask_cors import CORS

from config import Config
from database.db import init_db
from routes import auth_bp, dataset_bp, ml_bp


def create_app(config_class=Config):
    app = Flask(
        __name__,
        static_folder="../frontend",
        static_url_path=""
    )

    app.config.from_object(config_class)

    # Restrict cross-origin requests to local development origins.
    # The frontend served by this Flask app uses same-origin requests.
    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": [
                    "http://127.0.0.1:5000",
                    "http://localhost:5000"
                ]
            }
        }
    )

    # Ensure upload and model storage directories exist.
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["SAVED_MODELS_FOLDER"], exist_ok=True)

    # Initialize the database.
    init_db(app)

    # Register API blueprints.
    app.register_blueprint(auth_bp)
    app.register_blueprint(dataset_bp)
    app.register_blueprint(ml_bp)

    # Serve the frontend.
    @app.route("/")
    def index():
        return app.send_static_file("index.html")

    # Backend health-check endpoint.
    @app.route("/api/health", methods=["GET"])
    def health_check():
        return jsonify({
            "status": "healthy",
            "service": "Web-Based ML Model Evaluator Backend",
            "version": "1.0.0"
        }), 200

    return app


if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", 5000))

    print(
        f"Starting Web-Based ML Model Evaluator backend "
        f"on http://127.0.0.1:{port}"
    )

    app.run(host="0.0.0.0", port=port, debug=True)
