"""Owner-scoped CSV upload, validation, preview, replacement and statistics."""

import csv
import hashlib
import os
from uuid import uuid4

import pandas as pd
from flask import Blueprint, current_app, jsonify, request
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

from database.db import db
from ml.preprocessor import DataPreprocessor
from ml.trainer import ModelTrainer
from models.dataset import Dataset
from models.dataset_version import DatasetVersion
from routes.auth_utils import audit_event, current_user, login_required


dataset_bp = Blueprint("dataset", __name__, url_prefix="/api/dataset")


def _read_csv(path):
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as stream:
            header = next(csv.reader(stream, strict=True), None)
    except (UnicodeDecodeError, csv.Error, StopIteration):
        raise ValueError("Upload a readable UTF-8 CSV file.")
    if not header or len(header) < 2:
        raise ValueError("CSV must contain a header and at least two columns.")
    normalized = [str(value).strip() for value in header]
    if any(not value for value in normalized):
        raise ValueError("Every CSV column must have a non-empty header.")
    if len(set(normalized)) != len(normalized):
        raise ValueError("CSV column names must be unique.")
    try:
        frame = pd.read_csv(path, encoding="utf-8-sig", on_bad_lines="error")
    except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError):
        raise ValueError("CSV rows are malformed or the file is empty.")
    if frame.empty:
        raise ValueError("CSV must contain at least one data row.")
    if frame.shape[0] < 2:
        raise ValueError("CSV must contain at least two data rows for a train/test split.")
    if frame.shape[1] < 2:
        raise ValueError("CSV must contain at least two columns.")
    frame.columns = normalized
    return frame


def _store_upload(upload):
    if upload is None or not upload.filename:
        raise ValueError("Choose a CSV file to upload.")
    safe_name = secure_filename(upload.filename)
    if not safe_name or "." not in safe_name:
        raise ValueError("Upload a file with a .csv extension.")
    extension = safe_name.rsplit(".", 1)[1].lower()
    if extension not in current_app.config["ALLOWED_EXTENSIONS"]:
        raise ValueError("Only CSV files are supported.")

    upload_dir = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_dir, exist_ok=True)
    storage_name = f"{uuid4().hex}.csv"
    path = os.path.join(upload_dir, storage_name)
    upload.save(path)
    try:
        frame = _read_csv(path)
    except Exception:
        if os.path.exists(path):
            os.remove(path)
        raise
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return safe_name, path, frame, digest.hexdigest()


def _metadata(frame, checksum):
    result = DataPreprocessor.inspect(frame)
    result["sha256"] = checksum
    result["encoding"] = "UTF-8"
    return result


def _owned_dataset(dataset_id):
    user = current_user()
    return Dataset.query.filter_by(
        id=dataset_id, user_id=user.id, is_archived=False
    ).first()


def _public_dataset(dataset):
    return {
        "id": dataset.id,
        "filename": dataset.filename,
        "file_size": dataset.file_size,
        "row_count": dataset.row_count,
        "column_count": dataset.column_count,
        "metadata": dataset.metadata_json or {},
        "preprocessing": dataset.preprocessing_json or {},
        "target_column": dataset.target_column,
        "task_type": dataset.task_type,
        "version": dataset.versions[-1].version_number if dataset.versions else 0,
        "created_at": dataset.created_at.isoformat() if dataset.created_at else None,
    }


@dataset_bp.route("", methods=["GET"])
@login_required
def list_datasets():
    user = current_user()
    datasets = Dataset.query.filter_by(
        user_id=user.id, is_archived=False
    ).order_by(Dataset.created_at.desc()).all()
    return jsonify({"datasets": [_public_dataset(item) for item in datasets]}), 200


@dataset_bp.route("/upload", methods=["POST"])
@login_required
def upload_dataset():
    stored_path = None
    try:
        filename, stored_path, frame, checksum = _store_upload(
            request.files.get("file")
        )
        user = current_user()
        record = Dataset(
            user_id=user.id,
            filename=filename,
            file_path=stored_path,
            file_size=os.path.getsize(stored_path),
            row_count=len(frame),
            column_count=len(frame.columns),
            metadata_json=_metadata(frame, checksum),
        )
        db.session.add(record)
        db.session.flush()
        db.session.add(DatasetVersion(
            dataset_id=record.id,
            version_number=1,
            filename=filename,
            file_path=stored_path,
            file_size=record.file_size,
            row_count=record.row_count,
            column_count=record.column_count,
            metadata_json=record.metadata_json,
        ))
        db.session.commit()
        audit_event("dataset.uploaded", actor_user_id=user.id,
                    target_type="dataset", target_id=record.id)
        return jsonify({"dataset": _public_dataset(record)}), 201
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except RequestEntityTooLarge:
        db.session.rollback()
        if stored_path and os.path.exists(stored_path):
            os.remove(stored_path)
        raise
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Dataset upload failed")
        if stored_path and os.path.exists(stored_path):
            os.remove(stored_path)
        return jsonify({"error": "Dataset upload failed safely. Check the CSV and retry."}), 500


@dataset_bp.route("/<int:dataset_id>/replace", methods=["PUT"])
@login_required
def replace_dataset(dataset_id):
    existing = _owned_dataset(dataset_id)
    if existing is None:
        return jsonify({"error": "Dataset not found"}), 404
    new_path = None
    try:
        filename, new_path, frame, checksum = _store_upload(request.files.get("file"))
        next_version = max(
            (version.version_number for version in existing.versions), default=0
        ) + 1
        existing.filename = filename
        existing.file_path = new_path
        existing.file_size = os.path.getsize(new_path)
        existing.row_count = len(frame)
        existing.column_count = len(frame.columns)
        existing.metadata_json = _metadata(frame, checksum)
        db.session.add(DatasetVersion(
            dataset_id=existing.id,
            version_number=next_version,
            filename=filename,
            file_path=new_path,
            file_size=existing.file_size,
            row_count=existing.row_count,
            column_count=existing.column_count,
            metadata_json=existing.metadata_json,
        ))
        db.session.commit()
        user = current_user()
        audit_event("dataset.replaced", actor_user_id=user.id,
                    target_type="dataset", target_id=existing.id)
        return jsonify({"dataset": _public_dataset(existing)}), 200
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except RequestEntityTooLarge:
        db.session.rollback()
        if new_path and os.path.exists(new_path):
            os.remove(new_path)
        raise
    except Exception:
        db.session.rollback()
        if new_path and os.path.exists(new_path):
            os.remove(new_path)
        return jsonify({"error": "Dataset replacement failed; the prior dataset was kept."}), 500


@dataset_bp.route("/<int:dataset_id>", methods=["GET"])
@login_required
def dataset_metadata(dataset_id):
    dataset = _owned_dataset(dataset_id)
    if dataset is None:
        return jsonify({"error": "Dataset not found"}), 404
    return jsonify({"dataset": _public_dataset(dataset)}), 200


@dataset_bp.route("/<int:dataset_id>/preprocess", methods=["POST"])
@login_required
def configure_preprocessing(dataset_id):
    dataset = _owned_dataset(dataset_id)
    if dataset is None:
        return jsonify({"error": "Dataset not found"}), 404
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Valid JSON preprocessing options are required."}), 400
    options = {
        "missing_strategy": data.get("missing_strategy", "impute"),
        "numeric_imputer": data.get("numeric_imputer", "median"),
        "encode_categorical": data.get("encode_categorical", True),
        "scale_numeric": data.get("scale_numeric", True),
    }
    if options["missing_strategy"] not in {"impute", "drop_rows"}:
        return jsonify({"error": "Choose impute or drop_rows for missing values."}), 400
    if options["numeric_imputer"] not in {"median", "mean"}:
        return jsonify({"error": "Numeric imputation must use median or mean."}), 400
    if not isinstance(options["encode_categorical"], bool) or not isinstance(
        options["scale_numeric"], bool
    ):
        return jsonify({"error": "Encoding and scaling settings must be boolean."}), 400
    dataset.preprocessing_json = options
    db.session.commit()
    user = current_user()
    audit_event("dataset.preprocessing_configured", actor_user_id=user.id,
                target_type="dataset", target_id=dataset.id)
    return jsonify({
        "message": "Preprocessing options saved and will be applied during training.",
        "preprocessing": options,
    }), 200


@dataset_bp.route("/<int:dataset_id>/target", methods=["POST"])
@login_required
def select_target(dataset_id):
    dataset = _owned_dataset(dataset_id)
    if dataset is None:
        return jsonify({"error": "Dataset not found"}), 404
    data = request.get_json(silent=True)
    target_column = data.get("target_column") if isinstance(data, dict) else None
    try:
        frame = _read_csv(dataset.file_path)
        target = DataPreprocessor.validate_target(frame, target_column)
        task_type = DataPreprocessor.infer_task_type(target)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    dataset.target_column = target_column
    dataset.task_type = task_type
    db.session.commit()
    user = current_user()
    audit_event("dataset.target_selected", actor_user_id=user.id,
                target_type="dataset", target_id=dataset.id)
    return jsonify({
        "target_column": target_column,
        "task_type": task_type,
        "algorithms": ModelTrainer.SUPPORTED_ALGORITHMS[task_type],
    }), 200


@dataset_bp.route("/<int:dataset_id>/preview", methods=["GET"])
@login_required
def preview_dataset(dataset_id):
    dataset = _owned_dataset(dataset_id)
    if dataset is None:
        return jsonify({"error": "Dataset not found"}), 404
    try:
        frame = _read_csv(dataset.file_path)
        rows = frame.head(int(current_app.config["DATASET_PREVIEW_ROWS"]))
        return jsonify({
            "dataset_id": dataset.id,
            "columns": [str(column) for column in frame.columns],
            "rows": rows.astype(object).where(pd.notna(rows), None).to_dict("records"),
            "row_count": dataset.row_count,
        }), 200
    except Exception:
        current_app.logger.exception("Dataset preview failed")
        return jsonify({"error": "Dataset preview is unavailable."}), 500


@dataset_bp.route("/<int:dataset_id>/statistics", methods=["GET"])
@login_required
def dataset_statistics(dataset_id):
    dataset = _owned_dataset(dataset_id)
    if dataset is None:
        return jsonify({"error": "Dataset not found"}), 404
    try:
        frame = _read_csv(dataset.file_path)
        descriptions = frame.describe(include="all")
        summary = {}
        for column in frame.columns:
            values = descriptions[column].to_dict() if column in descriptions else {}
            summary[str(column)] = {
                str(key): (None if pd.isna(value) else value.item()
                           if hasattr(value, "item") else value)
                for key, value in values.items()
            }
        return jsonify({
            "dataset_id": dataset.id,
            "row_count": int(len(frame)),
            "column_count": int(len(frame.columns)),
            "columns": DataPreprocessor.inspect(frame)["columns"],
            "missing_values": {
                str(column): int(frame[column].isna().sum())
                for column in frame.columns
            },
            "summary": summary,
        }), 200
    except Exception:
        current_app.logger.exception("Dataset statistics failed")
        return jsonify({"error": "Dataset statistics are unavailable."}), 500
