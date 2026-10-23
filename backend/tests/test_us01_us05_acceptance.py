"""Acceptance checks limited to the US-01 through US-05 project scope."""

import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from app import create_app
from database.db import db
from models.dataset import Dataset
from models.evaluation import EvaluationResult
from models.model import MLModel
from models.user import User
from werkzeug.security import check_password_hash, generate_password_hash


class TestUS01ToUS05Acceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.storage = tempfile.TemporaryDirectory(
            prefix="us01-us05-acceptance-",
            dir=Path(__file__).resolve().parent,
        )
        storage_path = Path(cls.storage.name)

        class TestConfig:
            TESTING = True
            SECRET_KEY = "us01-us05-test-only"
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
        db.engine.dispose()
        cls.context.pop()
        cls.storage.cleanup()

    def setUp(self):
        db.session.rollback()
        db.session.remove()
        db.drop_all()
        db.create_all()
        self.client = self.app.test_client()
        self.username = f"us05_{uuid4().hex[:10]}"
        self.password = "StrongPass123!"

    def register_payload(self):
        return {
            "username": self.username,
            "email": f"{self.username}@example.com",
            "password": self.password,
        }

    def create_user(self):
        user = User(
            username=self.username,
            email=f"{self.username}@example.com",
            password_hash=generate_password_hash(self.password),
        )
        db.session.add(user)
        db.session.commit()
        return user

    def test_US01_repository_structure_is_present(self):
        """US-01: required frontend, backend, ML, database, README, and ignore files."""
        root = Path(__file__).resolve().parents[2]
        required_paths = (
            "frontend",
            "frontend/index.html",
            "frontend/login.html",
            "frontend/js/app.js",
            "backend/app.py",
            "backend/config.py",
            "backend/database/db.py",
            "backend/ml",
            "backend/models",
            "backend/routes",
            "backend/requirements.txt",
            "README.md",
            ".gitignore",
        )
        for relative_path in required_paths:
            with self.subTest(path=relative_path):
                self.assertTrue((root / relative_path).exists())

    def test_US02_required_schema_tables_and_relationships_exist(self):
        """US-02: user, dataset, model, evaluation tables and foreign keys."""
        root = Path(__file__).resolve().parents[2]
        self.assertTrue((root / "documents" / "Database_Schema.pdf").exists())

        expected_tables = {
            "users",
            "datasets",
            "models",
            "evaluation_results",
        }
        self.assertTrue(expected_tables.issubset(db.metadata.tables))

        expected_foreign_keys = {
            "datasets": {("user_id", "users", "id")},
            "models": {
                ("user_id", "users", "id"),
                ("dataset_id", "datasets", "id"),
            },
            "evaluation_results": {
                ("user_id", "users", "id"),
                ("model_id", "models", "id"),
            },
        }
        for table_name, expected in expected_foreign_keys.items():
            actual = {
                (
                    foreign_key.parent.name,
                    foreign_key.column.table.name,
                    foreign_key.column.name,
                )
                for foreign_key in db.metadata.tables[table_name].foreign_keys
            }
            self.assertTrue(expected.issubset(actual), table_name)

        self.assertIsNotNone(User.datasets.property.mapper.class_)
        self.assertIs(Dataset.user.property.mapper.class_, User)
        self.assertIs(MLModel.dataset.property.mapper.class_, Dataset)
        self.assertIs(EvaluationResult.model.property.mapper.class_, MLModel)

    def test_US03_health_and_frontend_assets_use_json_and_live_routes(self):
        """US-03: frontend can reach a JSON API and load its JS/CSS from Flask."""
        health = self.client.get("/api/health")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json["status"], "healthy")
        self.assertIn("application/json", health.content_type)
        health.close()

        for asset_path in ("/js/app.js", "/css/style.css"):
            with self.subTest(asset=asset_path):
                response = self.client.get(asset_path)
                try:
                    self.assertEqual(response.status_code, 200)
                finally:
                    response.close()

        login_page = self.client.get("/login")
        try:
            self.assertEqual(login_page.status_code, 200)
            self.assertIn(b'src="/js/app.js"', login_page.data)
            self.assertIn(b'href="/css/style.css"', login_page.data)
        finally:
            login_page.close()

    def test_FR_1_1_UT_1_valid_registration_is_saved_and_confirmed(self):
        response = self.client.post(
            "/api/auth/register", json=self.register_payload()
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json["message"], "Registration successful")
        self.assertIsNotNone(User.query.filter_by(username=self.username).first())

    def test_FR_1_1_UT_2_missing_or_invalid_registration_is_rejected(self):
        missing = self.client.post(
            "/api/auth/register", json={"username": self.username}
        )
        invalid_email_payload = self.register_payload()
        invalid_email_payload["email"] = "not-an-email"
        invalid_email = self.client.post(
            "/api/auth/register", json=invalid_email_payload
        )
        short_password_payload = self.register_payload()
        short_password_payload["password"] = "short"
        short_password = self.client.post(
            "/api/auth/register", json=short_password_payload
        )

        for response in (missing, invalid_email, short_password):
            self.assertEqual(response.status_code, 400)
            self.assertIn("error", response.json)
        self.assertEqual(User.query.count(), 0)

    def test_registration_enforces_the_eight_to_128_character_password_policy(self):
        minimum_payload = self.register_payload()
        minimum_payload["password"] = "a" * 8
        maximum_payload = self.register_payload()
        maximum_payload["username"] += "_max"
        maximum_payload["email"] = f"{maximum_payload['username']}@example.com"
        maximum_payload["password"] = "b" * 128
        too_long_payload = self.register_payload()
        too_long_payload["username"] += "_long"
        too_long_payload["email"] = f"{too_long_payload['username']}@example.com"
        too_long_payload["password"] = "c" * 129

        minimum = self.client.post("/api/auth/register", json=minimum_payload)
        maximum = self.client.post("/api/auth/register", json=maximum_payload)
        too_long = self.client.post("/api/auth/register", json=too_long_payload)

        self.assertEqual(minimum.status_code, 201)
        self.assertEqual(maximum.status_code, 201)
        self.assertEqual(too_long.status_code, 400)

    def test_FR_1_1_duplicate_username_and_email_are_rejected(self):
        payload = self.register_payload()
        first = self.client.post("/api/auth/register", json=payload)
        duplicate_username_payload = self.register_payload()
        duplicate_username_payload["email"] = f"other-{self.username}@example.com"
        duplicate_username = self.client.post(
            "/api/auth/register", json=duplicate_username_payload
        )
        duplicate_email_payload = self.register_payload()
        duplicate_email_payload["username"] = f"other_{self.username}"
        duplicate_email = self.client.post(
            "/api/auth/register", json=duplicate_email_payload
        )

        self.assertEqual(first.status_code, 201)
        self.assertEqual(duplicate_username.status_code, 409)
        self.assertEqual(duplicate_email.status_code, 409)

    def test_SEC_AUTH_2_registered_password_is_hashed(self):
        response = self.client.post(
            "/api/auth/register", json=self.register_payload()
        )
        saved = User.query.filter_by(username=self.username).first()
        self.assertEqual(response.status_code, 201)
        self.assertIsNotNone(saved)
        self.assertNotEqual(saved.password_hash, self.password)
        self.assertTrue(check_password_hash(saved.password_hash, self.password))

    def test_FR_1_2_UT_1_valid_credentials_create_session_and_redirect(self):
        user = self.create_user()
        response = self.client.post(
            "/api/auth/login",
            json={"username": self.username, "password": self.password},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["redirect_url"], "/")
        self.assertEqual(response.json["user"]["id"], user.id)
        with self.client.session_transaction() as session_data:
            self.assertEqual(session_data["user_id"], user.id)

    def test_FR_1_2_UT_2_wrong_password_and_unknown_user_share_error(self):
        self.create_user()
        wrong_password = self.client.post(
            "/api/auth/login",
            json={"username": self.username, "password": "WrongPass123!"},
        )
        unknown_user = self.client.post(
            "/api/auth/login",
            json={"username": "not-registered", "password": self.password},
        )
        oversized_password = self.client.post(
            "/api/auth/login",
            json={"username": self.username, "password": "x" * 129},
        )

        self.assertEqual(wrong_password.status_code, 401)
        self.assertEqual(unknown_user.status_code, 401)
        self.assertEqual(oversized_password.status_code, 401)
        self.assertEqual(wrong_password.json, unknown_user.json)
        self.assertEqual(wrong_password.json, oversized_password.json)

    def test_FR_1_4_ST_1_anonymous_dashboard_and_api_requests_are_denied(self):
        dashboard = self.client.get("/", follow_redirects=False)
        direct_dashboard = self.client.get("/index.html", follow_redirects=False)
        protected_api = self.client.get("/api/ml/algorithms")

        self.assertEqual(dashboard.status_code, 302)
        self.assertEqual(dashboard.headers["Location"], "/login")
        self.assertEqual(direct_dashboard.status_code, 302)
        self.assertEqual(protected_api.status_code, 401)
        self.assertEqual(protected_api.json["error"], "Authentication required")
        dashboard.close()
        direct_dashboard.close()
        protected_api.close()

    def test_authenticated_login_can_load_the_dashboard(self):
        self.create_user()
        self.client.post(
            "/api/auth/login",
            json={"username": self.username, "password": self.password},
        )
        dashboard = self.client.get("/")
        try:
            self.assertEqual(dashboard.status_code, 200)
        finally:
            dashboard.close()


if __name__ == "__main__":
    unittest.main()
