
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text

db = SQLAlchemy()


def init_db(app):
    """Initialize database with the Flask app context."""
    db.init_app(app)

    with app.app_context():
        # Import all models so tables are registered
        from models import (  # noqa: F401
            user, dataset, dataset_version, model, evaluation, security
        )

        db.create_all()
        _upgrade_existing_schema(app)
        _backfill_dataset_versions()


def _upgrade_existing_schema(app):
    """Add columns introduced after the initial project database was created."""
    additions = {
        "users": {
            "role": "VARCHAR(20) NOT NULL DEFAULT 'student'",
            "is_active": "BOOLEAN NOT NULL DEFAULT TRUE",
        },
        "datasets": {
            "is_archived": "BOOLEAN NOT NULL DEFAULT FALSE",
            "preprocessing_json": "JSON",
            "target_column": "VARCHAR(255)",
            "task_type": "VARCHAR(20)",
        },
        "models": {
            "dataset_version_id": "INTEGER",
            "task_type": "VARCHAR(20) NOT NULL DEFAULT 'classification'",
            "target_column": "VARCHAR(255) NOT NULL DEFAULT ''",
            "test_size": "FLOAT NOT NULL DEFAULT 0.2",
            "is_shared_with_instructors": "BOOLEAN NOT NULL DEFAULT FALSE",
        },
        "evaluation_results": {
            "visualization_json": "JSON",
        },
    }
    inspector = inspect(db.engine)
    with db.engine.begin() as connection:
        for table_name, columns in additions.items():
            existing = {column["name"] for column in inspector.get_columns(table_name)}
            for column_name, declaration in columns.items():
                if column_name not in existing:
                    connection.execute(
                        text(
                            f'ALTER TABLE "{table_name}" ADD COLUMN '
                            f'"{column_name}" {declaration}'
                        )
                    )


def _backfill_dataset_versions():
    """Preserve existing dataset files as version one after schema upgrades."""
    from models.dataset import Dataset
    from models.dataset_version import DatasetVersion

    for dataset in Dataset.query.all():
        if dataset.versions:
            continue
        db.session.add(DatasetVersion(
            dataset_id=dataset.id,
            version_number=1,
            filename=dataset.filename,
            file_path=dataset.file_path,
            file_size=dataset.file_size or 0,
            row_count=dataset.row_count or 0,
            column_count=dataset.column_count or 0,
            metadata_json=dataset.metadata_json or {},
        ))
    db.session.commit()
