import io
import os
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

from app import create_app
from database.db import db
from models.dataset import Dataset
from models.user import User
from sqlalchemy.exc import SQLAlchemyError


class TestDatasetUpload(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory(prefix="ml-evaluator-upload-tests-")

        class TestConfig:
            TESTING = True
            SECRET_KEY = "test-only"
            SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
            SQLALCHEMY_TRACK_MODIFICATIONS = False
            UPLOAD_FOLDER = os.path.join(cls.temp_dir.name, "uploads")
            SAVED_MODELS_FOLDER = os.path.join(cls.temp_dir.name, "models")
            MAX_CONTENT_LENGTH = 16 * 1024 * 1024

        cls.app = create_app(TestConfig)
        cls.context = cls.app.app_context()
        cls.context.push()
        db.create_all()

    @classmethod
    def tearDownClass(cls):
        db.session.remove()
        db.drop_all()
        cls.context.pop()
        cls.temp_dir.cleanup()

    def setUp(self):
        db.session.remove()
        self.client = self.app.test_client()
        self.user = User(
            username=f"u_{uuid4().hex[:12]}",
            email=f"{uuid4().hex}@example.com",
            password_hash="test-hash",
        )
        db.session.add(self.user)
        db.session.commit()

    def tearDown(self):
        db.session.query(Dataset).delete()
        db.session.query(User).delete()
        db.session.commit()
        for name in os.listdir(self.app.config["UPLOAD_FOLDER"]):
            os.remove(os.path.join(self.app.config["UPLOAD_FOLDER"], name))

    def authenticate(self, user_id=None):
        with self.client.session_transaction() as test_session:
            test_session["user_id"] = self.user.id if user_id is None else user_id

    def upload(self, contents, filename="data.csv", extra_fields=None):
        data = {"file": (io.BytesIO(contents), filename)}
        if extra_fields:
            data.update(extra_fields)
        return self.client.post("/api/dataset/upload", data=data, content_type="multipart/form-data")

    def test_valid_upload_persists_metadata_and_uses_unique_server_path(self):
        self.authenticate()
        contents = b"name,score\nAda,98\nLin,95\n"

        response = self.upload(contents, "../../students.csv")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json["filename"], "../../students.csv")
        self.assertEqual(response.json["row_count"], 2)
        self.assertEqual(response.json["column_count"], 2)
        self.assertEqual(response.json["columns"], ["name", "score"])
        dataset = db.session.get(Dataset, response.json["dataset_id"])
        self.assertIsNotNone(dataset)
        self.assertEqual(dataset.user_id, self.user.id)
        self.assertEqual(dataset.filename, "../../students.csv")
        self.assertEqual(dataset.file_size, len(contents))
        self.assertEqual(dataset.row_count, 2)
        self.assertEqual(dataset.column_count, 2)
        self.assertEqual(dataset.metadata_json, {"columns": ["name", "score"]})
        self.assertEqual(os.path.dirname(dataset.file_path), os.path.abspath(self.app.config["UPLOAD_FOLDER"]))
        self.assertTrue(os.path.isfile(dataset.file_path))
        with open(dataset.file_path, "rb") as saved:
            self.assertEqual(saved.read(), contents)

        second = self.upload(contents, "students.csv")
        self.assertEqual(second.status_code, 201)
        self.assertNotEqual(dataset.file_path, db.session.get(Dataset, second.json["dataset_id"]).file_path)

    def test_upload_requires_a_verified_session_user(self):
        response = self.upload(b"a\n1\n")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(Dataset.query.count(), 0)

    def test_request_user_id_cannot_supply_ownership(self):
        response = self.upload(b"a\n1\n", extra_fields={"user_id": str(self.user.id)})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(Dataset.query.count(), 0)

    def test_unknown_session_user_is_rejected(self):
        self.authenticate(user_id=self.user.id + 1000)
        response = self.upload(b"a\n1\n")
        self.assertEqual(response.status_code, 401)

    def test_missing_file_is_rejected(self):
        self.authenticate()
        response = self.client.post("/api/dataset/upload", data={})
        self.assertEqual(response.status_code, 400)
        self.assertIn("Choose a CSV", response.json["error"])

    def test_non_csv_extension_is_rejected(self):
        self.authenticate()
        response = self.upload(b"a\n1\n", "data.txt")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Unsupported file type", response.json["error"])

    def test_empty_file_is_rejected(self):
        self.authenticate()
        response = self.upload(b"")
        self.assertEqual(response.status_code, 400)
        self.assertIn("empty", response.json["error"].lower())

    def test_invalid_csvs_are_rejected_with_clear_errors(self):
        self.authenticate()
        invalid_files = [
            (b"\n\n", "no header"),
            (b"name,\nAda,1\n", "non-empty header"),
            (b"name,name\nAda,Lovelace\n", "unique"),
            (b"name,score\nAda\n", "same number of fields"),
            (b'name,score\n"Ada,98\n', "malformed"),
            (b"name,score\n", "at least one data row"),
            (b"name,score\n,\n,\n", "non-empty data row"),
            (b"name\n\xff\n", "UTF-8"),
        ]

        for contents, expected_message in invalid_files:
            with self.subTest(contents=contents):
                response = self.upload(contents)
                self.assertEqual(response.status_code, 400)
                self.assertIn(expected_message.lower(), response.json["error"].lower())
        self.assertEqual(Dataset.query.count(), 0)
        self.assertEqual(os.listdir(self.app.config["UPLOAD_FOLDER"]), [])

    def test_over_limit_upload_returns_json_413(self):
        self.authenticate()
        original_limit = self.app.config["MAX_CONTENT_LENGTH"]
        self.app.config["MAX_CONTENT_LENGTH"] = 128
        try:
            response = self.upload(b"a\n" + b"x" * 256 + b"\n")
        finally:
            self.app.config["MAX_CONTENT_LENGTH"] = original_limit
        self.assertEqual(response.status_code, 413)
        self.assertIn("size limit", response.json["error"].lower())
        self.assertEqual(Dataset.query.count(), 0)
        self.assertEqual(os.listdir(self.app.config["UPLOAD_FOLDER"]), [])

    def test_database_failure_rolls_back_and_removes_uploaded_file(self):
        self.authenticate()
        with patch("routes.dataset_routes.db.session.commit", side_effect=SQLAlchemyError("test failure")):
            response = self.upload(b"a\n1\n")

        self.assertEqual(response.status_code, 500)
        self.assertIn("could not be saved", response.json["error"].lower())
        self.assertEqual(Dataset.query.count(), 0)
        self.assertEqual(os.listdir(self.app.config["UPLOAD_FOLDER"]), [])


if __name__ == "__main__":
    unittest.main()
