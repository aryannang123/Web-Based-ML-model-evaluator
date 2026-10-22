import sqlite3
import tempfile
import unittest
from pathlib import Path

from app import create_app
from database.db import db
from models.dataset import Dataset
from models.dataset_version import DatasetVersion
from models.user import User


class TestDatabaseUpgrade(unittest.TestCase):
    def test_existing_v1_database_is_upgraded_and_dataset_is_versioned(self):
        with tempfile.TemporaryDirectory(
            prefix="ml-evaluator-migration-", dir=Path(__file__).resolve().parent
        ) as root:
            root = Path(root)
            database_path = root / "legacy.db"
            connection = sqlite3.connect(database_path)
            try:
                connection.executescript("""
                    CREATE TABLE users (
                        id INTEGER PRIMARY KEY, username VARCHAR(80) NOT NULL UNIQUE,
                        email VARCHAR(120) NOT NULL UNIQUE,
                        password_hash VARCHAR(256) NOT NULL,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                    );
                    CREATE TABLE datasets (
                        id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL,
                        filename VARCHAR(255) NOT NULL, file_path VARCHAR(512) NOT NULL,
                        file_size BIGINT, row_count INTEGER, column_count INTEGER,
                        metadata_json JSON,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                    );
                    CREATE TABLE models (
                        id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL,
                        dataset_id INTEGER NOT NULL, model_name VARCHAR(128) NOT NULL,
                        algorithm VARCHAR(128) NOT NULL, model_path VARCHAR(512),
                        status VARCHAR(32) NOT NULL DEFAULT 'pending', config_json JSON,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                    );
                    CREATE TABLE evaluation_results (
                        id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL,
                        model_id INTEGER NOT NULL, metrics_json JSON NOT NULL,
                        confusion_matrix_json JSON, report_json JSON,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                    );
                    INSERT INTO users (id, username, email, password_hash)
                        VALUES (1, 'legacy-student', 'legacy@example.org', 'hashed');
                    INSERT INTO datasets
                        (id, user_id, filename, file_path, file_size, row_count,
                         column_count, metadata_json)
                        VALUES (7, 1, 'old.csv', '/old/path.csv', 42, 2, 2,
                                '{"columns":[]}');
                """)
            finally:
                connection.close()

            class MigrationConfig:
                TESTING = True
                SECRET_KEY = "migration-test-secret"
                SQLALCHEMY_DATABASE_URI = f"sqlite:///{database_path.as_posix()}"
                SQLALCHEMY_TRACK_MODIFICATIONS = False
                UPLOAD_FOLDER = str(root / "uploads")
                SAVED_MODELS_FOLDER = str(root / "saved_models")

            app = create_app(MigrationConfig)
            try:
                with app.app_context():
                    user = User.query.filter_by(username="legacy-student").one()
                    dataset = Dataset.query.filter_by(id=7).one()
                    versions = DatasetVersion.query.filter_by(dataset_id=7).all()
                    self.assertEqual(user.role, "student")
                    self.assertTrue(user.is_active)
                    self.assertFalse(dataset.is_archived)
                    self.assertEqual(len(versions), 1)
                    self.assertEqual(versions[0].version_number, 1)
                    self.assertEqual(versions[0].filename, "old.csv")
            finally:
                with app.app_context():
                    db.session.remove()
                    db.engine.dispose()


if __name__ == "__main__":
    unittest.main()
