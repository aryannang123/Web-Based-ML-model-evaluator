import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from app import create_app
from database.db import db
from models.user import User
from werkzeug.security import check_password_hash


class TestRegistration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.storage = tempfile.TemporaryDirectory(
            prefix="ml-evaluator-registration-",
            dir=Path(__file__).resolve().parent,
        )
        storage_path = Path(cls.storage.name)

        class TestConfig:
            TESTING = True
            SECRET_KEY = "test-only"
            SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
            SQLALCHEMY_TRACK_MODIFICATIONS = False
            UPLOAD_FOLDER = str(storage_path / "uploads")
            SAVED_MODELS_FOLDER = str(storage_path / "models")

        cls.app = create_app(TestConfig)
        cls.context = cls.app.app_context()
        cls.context.push()

    @classmethod
    def tearDownClass(cls):
        db.session.remove()
        db.drop_all()
        cls.context.pop()
        cls.storage.cleanup()

    def setUp(self):
        self.client = self.app.test_client()

    def valid_user(self):
        unique = uuid4().hex[:8]
        return {
            "username": f"user_{unique}",
            "email": f"{unique}@example.com",
            "password": "StrongPass123!"
        }

    def test_successful_registration(self):
        response = self.client.post(
            "/api/auth/register", json=self.valid_user()
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.json["message"], "Registration successful"
        )

    def test_duplicate_email(self):
        user = self.valid_user()
        self.client.post("/api/auth/register", json=user)
        user["username"] = "another_user"
        response = self.client.post("/api/auth/register", json=user)
        self.assertEqual(response.status_code, 409)

    def test_duplicate_username(self):
        user = self.valid_user()
        self.client.post("/api/auth/register", json=user)
        user["email"] = f"{uuid4().hex[:8]}@example.com"
        response = self.client.post("/api/auth/register", json=user)
        self.assertEqual(response.status_code, 409)

    def test_missing_fields(self):
        response = self.client.post(
            "/api/auth/register", json={"username": "test"}
        )
        self.assertEqual(response.status_code, 400)

    def test_password_length_policy_has_eight_to_128_character_bounds(self):
        short = self.valid_user()
        short["password"] = "short7!"
        self.assertEqual(
            self.client.post("/api/auth/register", json=short).status_code, 400
        )

        too_long = self.valid_user()
        too_long["password"] = "p" * 129
        self.assertEqual(
            self.client.post("/api/auth/register", json=too_long).status_code, 400
        )

        accepted = self.valid_user()
        accepted["password"] = "p" * 128
        self.assertEqual(
            self.client.post("/api/auth/register", json=accepted).status_code, 201
        )

    def test_invalid_email(self):
        user = self.valid_user()
        user["email"] = "invalid-email"
        response = self.client.post("/api/auth/register", json=user)
        self.assertEqual(response.status_code, 400)

    def test_password_is_hashed(self):
        user = self.valid_user()
        response = self.client.post("/api/auth/register", json=user)
        self.assertEqual(response.status_code, 201)

        saved = User.query.filter_by(email=user["email"]).first()
        self.assertIsNotNone(saved)
        self.assertNotEqual(saved.password_hash, user["password"])
        self.assertTrue(
            check_password_hash(saved.password_hash, user["password"])
        )


if __name__ == "__main__":
    unittest.main()
