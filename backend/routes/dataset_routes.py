import csv
import io
import os
from uuid import uuid4

import pandas as pd
from flask import Blueprint, current_app, jsonify, request, session

from database.db import db
from models.dataset import Dataset
from models.user import User


dataset_bp = Blueprint("dataset", __name__, url_prefix="/api/dataset")


def _parse_csv(contents):
    """Validate a UTF-8 CSV and return its frame and original header names."""
    try:
        text = contents.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("The file must be a readable UTF-8 CSV.") from exc

    try:
        rows = csv.reader(io.StringIO(text, newline=""), strict=True)
        header = next((row for row in rows if row), None)
        if header is None:
            raise ValueError("The CSV file is empty or has no header row.")

        normalized_headers = [name.strip() for name in header]
        if not normalized_headers or any(not name for name in normalized_headers):
            raise ValueError("Every CSV column must have a non-empty header.")
        if len(set(normalized_headers)) != len(normalized_headers):
            raise ValueError("CSV column headers must be unique.")

        data_row_count = 0
        for row in rows:
            if not row:  # Ignore blank lines, as pandas does.
                continue
            if len(row) != len(header):
                raise ValueError(
                    "Each CSV row must contain the same number of fields as the header."
                )
            data_row_count += 1
    except csv.Error as exc:
        raise ValueError("The CSV file is malformed and could not be parsed.") from exc

    if data_row_count == 0:
        raise ValueError("The CSV file must contain at least one data row.")

    try:
        frame = pd.read_csv(io.BytesIO(contents), encoding="utf-8-sig")
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError, ValueError) as exc:
        raise ValueError("The CSV file is malformed and could not be parsed.") from exc

    if frame.empty or frame.shape[1] == 0 or frame.dropna(how="all").empty:
        raise ValueError("The CSV file must contain at least one non-empty data row.")

    return frame, header


def _authenticated_user():
    """Return the database user identified by the signed Flask session."""
    user_id = session.get("user_id")
    if isinstance(user_id, bool) or not isinstance(user_id, int) or user_id <= 0:
        return None
    return db.session.get(User, user_id)


@dataset_bp.route("/upload", methods=["POST"])
def upload_dataset():
    user = _authenticated_user()
    if user is None:
        return jsonify({"error": "Please log in before uploading a dataset."}), 401

    if "file" not in request.files:
        return jsonify({"error": "Choose a CSV file to upload."}), 400

    uploaded_file = request.files["file"]
    original_filename = uploaded_file.filename or ""
    if not original_filename:
        return jsonify({"error": "Choose a CSV file to upload."}), 400
    if not original_filename.lower().endswith(".csv"):
        return jsonify({"error": "Unsupported file type. Please choose a .csv file."}), 400
    if len(original_filename) > 255:
        return jsonify({"error": "The filename must be 255 characters or fewer."}), 400

    contents = uploaded_file.read()
    if not contents:
        return jsonify({"error": "The selected CSV file is empty."}), 400

    try:
        frame, columns = _parse_csv(contents)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    upload_folder = os.path.abspath(current_app.config["UPLOAD_FOLDER"])
    stored_name = f"{uuid4().hex}.csv"
    stored_path = os.path.abspath(os.path.join(upload_folder, stored_name))
    if os.path.commonpath([upload_folder, stored_path]) != upload_folder:
        return jsonify({"error": "Unable to safely store this upload."}), 500

    try:
        os.makedirs(upload_folder, exist_ok=True)
        with open(stored_path, "xb") as destination:
            destination.write(contents)

        dataset = Dataset(
            user_id=user.id,
            filename=original_filename,
            file_path=stored_path,
            file_size=len(contents),
            row_count=len(frame.index),
            column_count=len(columns),
            metadata_json={"columns": columns},
        )
        db.session.add(dataset)
        db.session.commit()
    except Exception:
        db.session.rollback()
        try:
            os.remove(stored_path)
        except FileNotFoundError:
            pass
        except OSError:
            current_app.logger.exception("Failed to remove an incomplete dataset upload")
        current_app.logger.exception("Failed to save uploaded dataset")
        return jsonify({"error": "The dataset could not be saved. Please try again."}), 500

    return jsonify({
        "message": "Dataset uploaded successfully.",
        "dataset_id": dataset.id,
        "filename": original_filename,
        "row_count": len(frame.index),
        "column_count": len(columns),
        "columns": columns,
        "file_size": len(contents),
    }), 201


@dataset_bp.route("/<int:dataset_id>/preview", methods=["GET"])
def preview_dataset(dataset_id):
    # TODO: US-12: Display dataset preview
    # Assigned to: @nidhipoojamrutha20
    # Steps: Read first N rows of CSV and return as JSON for frontend preview table
    return jsonify({"message": "Dataset preview endpoint ready for US-12 implementation"}), 501


@dataset_bp.route("/<int:dataset_id>/statistics", methods=["GET"])
def dataset_statistics(dataset_id):
    # TODO: US-13: Display dataset Statistics
    # Assigned to: @gaganraghavan
    # Steps: Compute summary statistics (mean, std, min, max, null counts)
    return jsonify({"message": "Dataset statistics endpoint ready for US-13 implementation"}), 501
