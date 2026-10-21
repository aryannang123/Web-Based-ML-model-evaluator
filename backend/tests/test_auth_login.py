import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from app import create_app
from database.db import db
from models.user import User
from werkzeug.security import generate_password_hash


class TestLogin(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.storage = tempfile.TemporaryDirectory(
            prefix="ml-evaluator-login-",
            dir=Path(__file__).resolve().parent,
        )
        storage_path = Path(cls.storage.name)

        class TestConfig:
            TESTING = True
            SECRET_KEY = "test-only-login-key"
            SESSION_COOKIE_HTTPONLY = True
            SESSION_COOKIE_SAMESITE = "Lax"
            SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
            SQLALCHEMY_TRACK_MODIFICATIONS = False
            UPLOAD_FOLDER = str(storage_path / "uploads")
            SAVED_MODELS_FOLDER = str(storage_path / "models")

        cls.app = create_app(TestConfig)
        cls.context = cls.app.app_context()
        cls.context.push()
        db.create_all()

    @classmethod
    def tearDownClass(cls):
        db.session.remove()
        db.drop_all()
        cls.context.pop()
        cls.storage.cleanup()

    def setUp(self):
        self.client = self.app.test_client()
        self.username = f"login_{uuid4().hex[:10]}"
        self.password = "StrongPass123!"
        self.user = User(
            username=self.username,
            email=f"{self.username}@example.com",
            password_hash=generate_password_hash(self.password),
        )
        db.session.add(self.user)
        db.session.commit()

    def tearDown(self):
        db.session.delete(self.user)
        db.session.commit()

    def test_valid_credentials_create_session_and_return_dashboard_redirect(self):
        response = self.client.post(
            "/api/auth/login",
            json={"username": self.username, "password": self.password},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["redirect_url"], "/")
        self.assertEqual(response.json["user"]["username"], self.username)
        with self.client.session_transaction() as session_data:
            self.assertEqual(session_data["user_id"], self.user.id)
            self.assertEqual(session_data["username"], self.username)

        session_response = self.client.get("/api/auth/session")
        self.assertTrue(session_response.json["authenticated"])

    def test_invalid_password_and_unknown_username_return_same_error(self):
        bad_password = self.client.post(
            "/api/auth/login",
            json={"username": self.username, "password": "WrongPass123!"},
        )
        unknown_user = self.client.post(
            "/api/auth/login",
            json={"username": "unknown-user", "password": self.password},
        )

        self.assertEqual(bad_password.status_code, 401)
        self.assertEqual(unknown_user.status_code, 401)
        self.assertEqual(bad_password.json, unknown_user.json)
        self.assertEqual(
            bad_password.json["error"], "Invalid username or password"
        )
        with self.client.session_transaction() as session_data:
            self.assertNotIn("user_id", session_data)

    def test_missing_or_invalid_login_payload_returns_clear_client_error(self):
        missing_password = self.client.post(
            "/api/auth/login", json={"username": self.username}
        )
        invalid_json = self.client.post(
            "/api/auth/login",
            data="not-json",
            content_type="text/plain",
        )

        self.assertEqual(missing_password.status_code, 400)
        self.assertIn("required", missing_password.json["error"])
        self.assertEqual(invalid_json.status_code, 400)
        self.assertIn("JSON", invalid_json.json["error"])

    def test_unauthenticated_users_cannot_access_dashboard_or_protected_apis(self):
        dashboard = self.client.get("/", follow_redirects=False)
        direct_dashboard_file = self.client.get(
            "/index.html", follow_redirects=False
        )
        algorithms = self.client.get("/api/ml/algorithms")
        upload = self.client.post("/api/dataset/upload")
        preview = self.client.get("/api/dataset/1/preview")
        statistics = self.client.get("/api/dataset/1/statistics")
        train = self.client.post("/api/ml/train")
        evaluate = self.client.post("/api/ml/evaluate")

        self.assertEqual(dashboard.status_code, 302)
        self.assertEqual(dashboard.headers["Location"], "/login")
        self.assertEqual(direct_dashboard_file.status_code, 302)
        self.assertEqual(algorithms.status_code, 401)
        self.assertEqual(upload.status_code, 401)
        self.assertEqual(preview.status_code, 401)
        self.assertEqual(statistics.status_code, 401)
        self.assertEqual(train.status_code, 401)
        self.assertEqual(evaluate.status_code, 401)
        self.assertTrue(algorithms.is_json)

    def test_stale_session_cannot_open_dashboard(self):
        with self.client.session_transaction() as session_data:
            session_data["user_id"] = 999999

        dashboard = self.client.get("/", follow_redirects=False)

        self.assertEqual(dashboard.status_code, 302)
        self.assertEqual(dashboard.headers["Location"], "/login")
        with self.client.session_transaction() as session_data:
            self.assertNotIn("user_id", session_data)

    def test_authenticated_user_can_open_dashboard_and_use_protected_api(self):
        login = self.client.post(
            "/api/auth/login",
            json={"username": self.username, "password": self.password},
        )
        self.assertEqual(login.status_code, 200)

        dashboard = self.client.get("/")
        direct_dashboard_file = self.client.get("/index.html")
        algorithms = self.client.get("/api/ml/algorithms")

        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(direct_dashboard_file.status_code, 200)
        self.assertEqual(algorithms.status_code, 200)
        self.assertIn("classification", algorithms.json)

    def test_login_clears_prior_session_data_and_sets_cookie_flags(self):
        with self.client.session_transaction() as session_data:
            session_data["untrusted_old_value"] = "discard-me"

        response = self.client.post(
            "/api/auth/login",
            json={"username": self.username, "password": self.password},
        )

        self.assertEqual(response.status_code, 200)
        with self.client.session_transaction() as session_data:
            self.assertNotIn("untrusted_old_value", session_data)
        set_cookie = response.headers.get("Set-Cookie", "")
        self.assertIn("HttpOnly", set_cookie)
        self.assertIn("SameSite=Lax", set_cookie)


if __name__ == "__main__":
    unittest.main()
