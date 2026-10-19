from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from database.db import db
from models.dataset import Dataset
from ml.preprocessor import DataPreprocessor
import os
import pandas as pd

dataset_bp = Blueprint("dataset", __name__, url_prefix="/api/dataset")

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in current_app.config["ALLOWED_EXTENSIONS"]

@dataset_bp.route("/upload", methods=["POST"])
def upload_dataset():
    if "file" not in request.files:
        return jsonify({"error": "No file part in request"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Only CSV files are supported"}), 400

    user_id = request.form.get("user_id", 1, type=int)

    filename = secure_filename(file.filename)
    os.makedirs(current_app.config["UPLOAD_FOLDER"], exist_ok=True)
    filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], f"{user_id}_{filename}")
    file.save(filepath)

    try:
        df = pd.read_csv(filepath)
        if len(df) < 5:
            os.remove(filepath)
            return jsonify({"error": "Dataset must contain at least 5 rows"}), 400

        inspection = DataPreprocessor.inspect_dataset(df)

        dataset = Dataset(
            user_id=user_id,
            filename=filename,
            file_path=filepath,
            row_count=inspection["total_rows"],
            column_count=inspection["total_columns"]
        )
        dataset.set_columns(inspection["columns"])

        db.session.add(dataset)
        db.session.commit()

        return jsonify({
            "message": "Dataset uploaded successfully",
            "dataset": dataset.to_dict(),
            "preview": df.head(10).to_dict(orient="records")
        }), 201

    except Exception as e:
        if os.path.exists(filepath):
            os.remove(filepath)
        return jsonify({"error": f"Failed to process CSV file: {str(e)}"}), 400

@dataset_bp.route("/<int:dataset_id>/preview", methods=["GET"])
def preview_dataset(dataset_id):
    dataset = Dataset.query.get_or_404(dataset_id)
    if not os.path.exists(dataset.file_path):
        return jsonify({"error": "Dataset file not found on disk"}), 404

    df = pd.read_csv(dataset.file_path)
    return jsonify({
        "dataset": dataset.to_dict(),
        "preview": df.head(10).to_dict(orient="records"),
        "statistics": df.describe(include="all").to_dict()
    }), 200
