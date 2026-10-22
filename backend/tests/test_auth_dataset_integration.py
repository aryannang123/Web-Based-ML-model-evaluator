import io
import os
import tempfile
import unittest
from uuid import uuid4

from app import create_app
from database.db import db
from models.dataset import Dataset
from models.user import User
from werkzeug.security import check_password_hash


class TestAuthDatasetIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory(
            prefix="ml-evaluator-auth-upload-tests-"
        )

        class TestConfig:
            TESTING = True
            SECRET_KEY = "test-only-auth-upload-key"
            SESSION_COOKIE_HTTPONLY = True
            SESSION_COOKIE_SAMESITE = "Lax"
            SESSION_COOKIE_SECURE = False
            SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
            SQLALCHEMY_TRACK_MODIFICATIONS = False
            UPLOAD_FOLDER = os.path.join(cls.temp_dir.name, "uploads")
            SAVED_MODELS_FOLDER = os.path.join(cls.temp_dir.name, "models")

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
        self.user_data = {
            "username": f"flow_{uuid4().hex[:12]}",
            "email": f"{uuid4().hex}@example.com",
            "password": "StrongPass123!",
        }

    def tearDown(self):
        db.session.rollback()
        Dataset.query.delete()
        User.query.delete()
        db.session.commit()
        upload_folder = self.app.config["UPLOAD_FOLDER"]
        if os.path.isdir(upload_folder):
            for name in os.listdir(upload_folder):
                os.remove(os.path.join(upload_folder, name))

    def register_and_login(self):
        registration = self.client.post(
            "/api/auth/register", json=self.user_data
        )
        self.assertEqual(registration.status_code, 201)

        user = User.query.filter_by(username=self.user_data["username"]).one()
        self.assertTrue(
            check_password_hash(user.password_hash, self.user_data["password"])
        )

        login = self.client.post(
            "/api/auth/login",
            json={
                "username": self.user_data["username"],
                "password": self.user_data["password"],
            },
        )
        return user, login

    def test_registration_login_dashboard_refresh_and_session_cookie(self):
        user, login = self.register_and_login()

        self.assertEqual(login.status_code, 200)
        self.assertEqual(login.json["redirect_url"], "/")
        cookie = login.headers.get("Set-Cookie", "")
        self.assertIn("session=", cookie)
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=Lax", cookie)
        with self.client.session_transaction() as session_data:
            self.assertEqual(session_data["user_id"], user.id)

        dashboard = self.client.get("/", follow_redirects=False)
        self.assertEqual(dashboard.status_code, 200)
        self.assertIn(b"current-user", dashboard.data)

        # A second page request represents a browser refresh with the same cookie.
        refreshed_dashboard = self.client.get("/", follow_redirects=False)
        self.assertEqual(refreshed_dashboard.status_code, 200)
        session_status = self.client.get("/api/auth/session")
        self.assertEqual(session_status.json["authenticated"], True)
        self.assertEqual(session_status.json["user"]["id"], user.id)

        login_page = self.client.get("/login", follow_redirects=False)
        self.assertEqual(login_page.status_code, 302)
        self.assertEqual(login_page.headers["Location"], "/")

    def test_login_page_loads_the_javascript_that_handles_credentials(self):
        page = self.client.get("/login")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b'src="/js/app.js"', page.data)

        script = self.client.get("/js/app.js")
        self.assertEqual(script.status_code, 200)
        self.assertIn(b'credentials: "same-origin"', script.data)
        self.assertIn(b"/auth/login", script.data)

    def test_authenticated_registration_login_and_csv_upload_are_one_flow(self):
        user, login = self.register_and_login()
        self.assertEqual(login.status_code, 200)

        contents = b"name,score\nAda,98\nLin,95\n"
        response = self.client.post(
            "/api/dataset/upload",
            data={"file": (io.BytesIO(contents), "students.csv")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json["filename"], "students.csv")
        self.assertEqual(response.json["row_count"], 2)
        self.assertEqual(response.json["column_count"], 2)

        dataset = db.session.get(Dataset, response.json["dataset_id"])
        self.assertIsNotNone(dataset)
        self.assertEqual(dataset.user_id, user.id)
        self.assertEqual(dataset.filename, "students.csv")
        self.assertEqual(dataset.metadata_json, {"columns": ["name", "score"]})
        self.assertEqual(
            os.path.dirname(dataset.file_path),
            os.path.abspath(self.app.config["UPLOAD_FOLDER"]),
        )
        self.assertTrue(os.path.isfile(dataset.file_path))
        with open(dataset.file_path, "rb") as saved_file:
            self.assertEqual(saved_file.read(), contents)

    def test_invalid_credentials_are_rejected_and_do_not_authenticate(self):
        registration = self.client.post(
            "/api/auth/register", json=self.user_data
        )
        self.assertEqual(registration.status_code, 201)

        login = self.client.post(
            "/api/auth/login",
            json={
                "username": self.user_data["username"],
                "password": "IncorrectPass123!",
            },
        )
        self.assertEqual(login.status_code, 401)
        self.assertEqual(login.json["error"], "Invalid username or password")
        with self.client.session_transaction() as session_data:
            self.assertNotIn("user_id", session_data)

    def test_unauthenticated_csv_upload_returns_401(self):
        response = self.client.post(
            "/api/dataset/upload",
            data={"file": (io.BytesIO(b"name\nAda\n"), "students.csv")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(Dataset.query.count(), 0)


if __name__ == "__main__":
    unittest.main()
