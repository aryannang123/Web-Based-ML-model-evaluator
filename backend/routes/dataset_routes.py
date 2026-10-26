
import csv
import io
import os
from uuid import uuid4

import pandas as pd
from flask import Blueprint, current_app, g, jsonify, request

from database.db import db
from models.dataset import Dataset
from routes.auth_utils import (
    get_owned_dataset,
    login_required,
    owned_dataset_query,
)


dataset_bp = Blueprint("dataset", __name__, url_prefix="/api/dataset")


def _parse_csv(contents, min_data_rows=2, min_data_columns=2):
    """Validate a UTF-8 CSV and return its DataFrame and original headers."""
    if b"\x00" in contents:
        raise ValueError(
            "The CSV contains binary NUL characters and cannot be read."
        )

    try:
        text = contents.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError(
            "The file must be a readable UTF-8 CSV."
        ) from exc

    try:
        rows = csv.reader(io.StringIO(text, newline=""), strict=True)
        header = next((row for row in rows if row), None)

        if header is None:
            raise ValueError(
                "The CSV file is empty or has no header row."
            )

        normalized_headers = [name.strip() for name in header]

        if any(not name for name in normalized_headers):
            raise ValueError(
                "Every CSV column must have a non-empty header."
            )

        if len(set(normalized_headers)) != len(normalized_headers):
            raise ValueError(
                "CSV column headers must be unique."
            )

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
                    "Each CSV row must contain the same number of "
                    "fields as the header."
                )

            if all(not value.strip() for value in row):
                raise ValueError(
                    "The CSV contains an empty data row."
                )

    except csv.Error as exc:
        raise ValueError(
            "The CSV file is malformed and could not be parsed."
        ) from exc

    try:
        frame = pd.read_csv(
            io.BytesIO(contents),
            encoding="utf-8-sig",
        )
    except (
        pd.errors.EmptyDataError,
        pd.errors.ParserError,
        UnicodeDecodeError,
        ValueError,
    ) as exc:
        raise ValueError(
            "The CSV file is malformed and could not be parsed."
        ) from exc

    frame = frame.dropna(how="all")

    if frame.shape[1] < min_data_columns:
        raise ValueError(
            f"The CSV must contain at least {min_data_columns} columns "
            "(one feature and one target)."
        )

    if len(frame.index) < min_data_rows:
        raise ValueError(
            f"The CSV must contain at least {min_data_rows} "
            "non-empty data rows."
        )

    usable_columns = frame.notna().any(axis=0).sum()

    if usable_columns < min_data_columns:
        raise ValueError(
            f"The CSV must contain at least {min_data_columns} "
            "columns with data."
        )

    return frame, header


def _persist_dataset(dataset):
    """Persist a newly uploaded dataset."""
    db.session.add(dataset)
    db.session.commit()


def _dataset_response(dataset):
    """Return dataset metadata without exposing its server file path."""
    return {
        "id": dataset.id,
        "filename": dataset.filename,
        "file_size": dataset.file_size,
        "row_count": dataset.row_count,
        "column_count": dataset.column_count,
        "metadata": dataset.metadata_json,
        "created_at": (
            dataset.created_at.isoformat()
            if dataset.created_at
            else None
        ),
    }


def _store_upload(contents, upload_folder):
    """Save uploaded bytes to a unique path inside the upload directory."""
    upload_folder = os.path.abspath(upload_folder)
    os.makedirs(upload_folder, exist_ok=True)

    stored_path = os.path.abspath(
        os.path.join(upload_folder, f"{uuid4().hex}.csv")
    )

    if os.path.commonpath([upload_folder, stored_path]) != upload_folder:
        raise ValueError("Unable to safely store this upload.")

    with open(stored_path, "xb") as destination:
        destination.write(contents)

    return stored_path


def _remove_file(path):
    """Best-effort cleanup for a file created by an upload request."""
    if not path:
        return

    try:
        os.remove(path)
    except FileNotFoundError:
        pass
    except OSError:
        current_app.logger.exception(
            "Failed to remove dataset file: %s", path
        )


def _read_and_validate_upload():
    """Read and validate a CSV from the current multipart request."""
    if "file" not in request.files:
        return None, None, None, (
            jsonify({"error": "Choose a CSV file to upload."}),
            400,
        )

    uploaded_file = request.files["file"]
    filename = uploaded_file.filename or ""

    if not filename:
        return None, None, None, (
            jsonify({"error": "Choose a CSV file to upload."}),
            400,
        )

    if not filename.lower().endswith(".csv"):
        return None, None, None, (
            jsonify({
                "error": "Unsupported file type. Please choose a .csv file."
            }),
            400,
        )

    if len(filename) > 255:
        return None, None, None, (
            jsonify({
                "error": "The filename must be 255 characters or fewer."
            }),
            400,
        )

    contents = uploaded_file.read()

    if not contents:
        return None, None, None, (
            jsonify({"error": "The selected CSV file is empty."}),
            400,
        )

    try:
        frame, columns = _parse_csv(
            contents,
            min_data_rows=current_app.config.get("MIN_DATA_ROWS", 2),
            min_data_columns=current_app.config.get("MIN_DATA_COLUMNS", 2),
        )
    except ValueError as exc:
        return None, None, None, (
            jsonify({"error": str(exc)}),
            400,
        )

    return (filename, contents, (frame, columns)), None, None, None


@dataset_bp.route("", methods=["GET"])
@login_required
def list_datasets():
    """List datasets belonging to the logged-in user."""
    datasets = (
        owned_dataset_query(g.current_user.id)
        .order_by(Dataset.created_at.asc(), Dataset.id.asc())
        .all()
    )

    return jsonify({
        "datasets": [_dataset_response(item) for item in datasets]
    }), 200


@dataset_bp.route("/<int:dataset_id>", methods=["GET"])
@login_required
def get_dataset(dataset_id):
    """Retrieve an owned dataset's metadata."""
    dataset = get_owned_dataset(dataset_id, g.current_user.id)

    if dataset is None:
        return jsonify({"error": "Dataset not found"}), 404

    return jsonify({"dataset": _dataset_response(dataset)}), 200


@dataset_bp.route("/upload", methods=["POST"])
@login_required
def upload_dataset():
    """Upload a new dataset without replacing existing dataset records."""
    result, _, _, error_response = _read_and_validate_upload()

    if error_response is not None:
        return error_response

    filename, contents, parsed = result
    frame, columns = parsed
    stored_path = None

    try:
        stored_path = _store_upload(
            contents,
            current_app.config["UPLOAD_FOLDER"],
        )

        dataset = Dataset(
            user_id=g.current_user.id,
            filename=filename,
            file_path=stored_path,
            file_size=len(contents),
            row_count=len(frame.index),
            column_count=len(columns),
            metadata_json={"columns": columns},
        )

        _persist_dataset(dataset)

    except Exception:
        db.session.rollback()
        _remove_file(stored_path)

        current_app.logger.exception(
            "Failed to save uploaded dataset"
        )

        return jsonify({
            "error": "The dataset could not be saved. Please try again."
        }), 500

    return jsonify({
        "message": "Dataset uploaded successfully.",
        "dataset_id": dataset.id,
        "filename": filename,
        "row_count": len(frame.index),
        "column_count": len(columns),
        "columns": columns,
        "file_size": len(contents),
    }), 201


@dataset_bp.route("/<int:dataset_id>/replace", methods=["POST"])
@login_required
def replace_dataset(dataset_id):
    """Replace an owned dataset while preserving its database ID."""
    dataset = get_owned_dataset(dataset_id, g.current_user.id)

    if dataset is None:
        return jsonify({"error": "Dataset not found"}), 404

    result, _, _, error_response = _read_and_validate_upload()

    if error_response is not None:
        return error_response

    filename, contents, parsed = result
    frame, columns = parsed
    old_path = dataset.file_path
    stored_path = None

    try:
        stored_path = _store_upload(
            contents,
            current_app.config["UPLOAD_FOLDER"],
        )

        dataset.filename = filename
        dataset.file_path = stored_path
        dataset.file_size = len(contents)
        dataset.row_count = len(frame.index)
        dataset.column_count = len(columns)
        dataset.metadata_json = {"columns": columns}

        db.session.commit()

    except Exception:
        db.session.rollback()
        _remove_file(stored_path)

        current_app.logger.exception(
            "Failed to replace dataset %s", dataset_id
        )

        return jsonify({
            "error": (
                "The dataset could not be replaced. "
                "Please try again."
            )
        }), 500

    # Delete the old file only after the database commit succeeds.
    if (
        old_path
        and os.path.abspath(old_path) != os.path.abspath(stored_path)
    ):
        _remove_file(old_path)

    return jsonify({
        "message": "Dataset replaced successfully.",
        "dataset_id": dataset.id,
        "filename": dataset.filename,
        "row_count": dataset.row_count,
        "column_count": dataset.column_count,
        "columns": columns,
        "file_size": dataset.file_size,
    }), 200


@dataset_bp.route("/<int:dataset_id>/preview", methods=["GET"])
@login_required
def preview_dataset(dataset_id):
    """Dataset preview endpoint reserved for US-12."""
    if get_owned_dataset(dataset_id, g.current_user.id) is None:
        return jsonify({"error": "Dataset not found"}), 404

    # TODO: US-12: Display dataset preview.
    return jsonify({
        "message": "Dataset preview endpoint ready for US-12 implementation"
    }), 501


@dataset_bp.route("/<int:dataset_id>/statistics", methods=["GET"])
@login_required
def dataset_statistics(dataset_id):
    """Dataset statistics endpoint reserved for US-13."""
    if get_owned_dataset(dataset_id, g.current_user.id) is None:
        return jsonify({"error": "Dataset not found"}), 404

    # TODO: US-13: Display dataset statistics.
    return jsonify({
        "message": "Dataset statistics endpoint ready for US-13 implementation"
    }), 501
