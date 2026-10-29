import csv
import io
import math
import os
from uuid import uuid4

import pandas as pd
from flask import Blueprint, current_app, g, jsonify, request

from database.db import db
from models.dataset import Dataset
from routes.auth_utils import get_owned_dataset, login_required, owned_dataset_query


dataset_bp = Blueprint("dataset", __name__, url_prefix="/api/dataset")


def _parse_csv(contents, min_data_rows=2, min_data_columns=2):
    """Validate a UTF-8 CSV and return its frame and original header names."""
    if b"\x00" in contents:
        raise ValueError("The CSV contains binary NUL characters and cannot be read.")

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
        if len(header) < min_data_columns:
            raise ValueError(
                f"The CSV must contain at least {min_data_columns} columns "
                "(one feature and one target)."
            )

        for row in rows:
            if not row:
                continue
            if len(row) != len(header):
                raise ValueError(
                    "Each CSV row must contain the same number of fields as the header."
                )
            if all(not value.strip() for value in row):
                raise ValueError("The CSV contains an empty data row.")
    except csv.Error as exc:
        raise ValueError("The CSV file is malformed and could not be parsed.") from exc

    try:
        frame = pd.read_csv(io.BytesIO(contents), encoding="utf-8-sig")
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError, ValueError) as exc:
        raise ValueError("The CSV file is malformed and could not be parsed.") from exc

    frame = frame.dropna(how="all")
    if frame.shape[1] < min_data_columns:
        raise ValueError(
            f"The CSV must contain at least {min_data_columns} columns "
            "(one feature and one target)."
        )
    if len(frame.index) < min_data_rows:
        raise ValueError(
            f"The CSV must contain at least {min_data_rows} non-empty data rows."
        )
    usable_columns = frame.notna().any(axis=0).sum()
    if usable_columns < min_data_columns:
        raise ValueError(
            f"The CSV must contain at least {min_data_columns} columns with data."
        )

    return frame, header


def _persist_dataset(dataset):
    """Persist a newly stored upload row."""
    db.session.add(dataset)
    db.session.commit()


def _dataset_response(dataset):
    """Return owner-visible metadata without exposing a server filesystem path."""
    return {
        "id": dataset.id,
        "filename": dataset.filename,
        "file_size": dataset.file_size,
        "row_count": dataset.row_count,
        "column_count": dataset.column_count,
        "metadata": dataset.metadata_json,
        "created_at": dataset.created_at.isoformat() if dataset.created_at else None,
    }


@dataset_bp.route("", methods=["GET"])
@login_required
def list_datasets():
    datasets = owned_dataset_query(g.current_user.id).order_by(
        Dataset.created_at.asc(), Dataset.id.asc()
    ).all()
    return jsonify({"datasets": [_dataset_response(item) for item in datasets]}), 200


@dataset_bp.route("/<int:dataset_id>", methods=["GET"])
@login_required
def get_dataset(dataset_id):
    dataset = get_owned_dataset(dataset_id, g.current_user.id)
    if dataset is None:
        return jsonify({"error": "Dataset not found"}), 404
    return jsonify({"dataset": _dataset_response(dataset)}), 200


@dataset_bp.route("/upload", methods=["POST"])
@login_required
def upload_dataset():
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
        frame, columns = _parse_csv(
            contents,
            min_data_rows=current_app.config.get("MIN_DATA_ROWS", 2),
            min_data_columns=current_app.config.get("MIN_DATA_COLUMNS", 2),
        )
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
            user_id=g.current_user.id,
            filename=original_filename,
            file_path=stored_path,
            file_size=len(contents),
            row_count=len(frame.index),
            column_count=len(columns),
            metadata_json={"columns": columns},
        )
        _persist_dataset(dataset)
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
@login_required
def preview_dataset(dataset_id):
    dataset = get_owned_dataset(dataset_id, g.current_user.id)
    if dataset is None:
        return jsonify({"error": "Dataset not found"}), 404

    # Uploads are stored beneath UPLOAD_FOLDER. Validate the persisted path as
    # well, so a damaged database row cannot make this endpoint read an
    # arbitrary server file.
    upload_folder = os.path.realpath(current_app.config["UPLOAD_FOLDER"])
    stored_path = os.path.realpath(dataset.file_path)
    try:
        inside_upload_folder = os.path.commonpath([upload_folder, stored_path]) == upload_folder
    except ValueError:
        inside_upload_folder = False
    if not inside_upload_folder or not os.path.isfile(stored_path):
        return jsonify({"error": "The dataset file is missing or unavailable."}), 404

    try:
        # Chunked parsing bounds memory use while still counting every row.
        # Dtypes are combined across chunks so later mixed values are noticed.
        sample_rows = []
        column_names = None
        inferred_dtypes = {}
        row_count = 0
        for chunk in pd.read_csv(stored_path, chunksize=10000):
            if column_names is None:
                column_names = [str(name) for name in chunk.columns]
                inferred_dtypes = {str(name): str(chunk[name].dtype) for name in chunk.columns}
            else:
                for name in chunk.columns:
                    key = str(name)
                    previous = inferred_dtypes[key]
                    current = str(chunk[name].dtype)
                    if previous == current:
                        continue
                    if previous.startswith(("int", "uint")) and current.startswith(("int", "uint")):
                        continue
                    if previous.startswith(("int", "uint", "float")) and current.startswith(("int", "uint", "float")):
                        inferred_dtypes[key] = "float64"
                    else:
                        inferred_dtypes[key] = "object"
            row_count += len(chunk.index)
            if len(sample_rows) < 10:
                sample_rows.extend(chunk.head(10 - len(sample_rows)).to_dict(orient="records"))
    except (OSError, PermissionError):
        return jsonify({"error": "The dataset file could not be read."}), 500
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError, ValueError) as exc:
        current_app.logger.info("Could not parse dataset preview for dataset %s: %s", dataset_id, exc)
        return jsonify({"error": "The dataset CSV is malformed or unreadable."}), 400

    def json_value(value):
        if pd.isna(value):
            return None
        if hasattr(value, "item"):
            value = value.item()
        if isinstance(value, float) and not math.isfinite(value):
            return None
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        return str(value)

    rows = [
        {str(name): json_value(value) for name, value in row.items()}
        for row in sample_rows
    ]
    return jsonify({
        "dataset_id": dataset.id,
        "columns": column_names or [],
        "data_types": {name: inferred_dtypes[name] for name in (column_names or [])},
        "rows": rows,
        "row_count": row_count,
        "column_count": len(column_names or []),
        "sample_size": len(rows),
    }), 200


@dataset_bp.route("/<int:dataset_id>/statistics", methods=["GET"])
@login_required
def dataset_statistics(dataset_id):
    if get_owned_dataset(dataset_id, g.current_user.id) is None:
        return jsonify({"error": "Dataset not found"}), 404
    # TODO: US-13: Display dataset statistics.
    return jsonify({"message": "Dataset statistics endpoint ready for US-13 implementation"}), 501
