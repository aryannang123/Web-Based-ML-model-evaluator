import unittest

from app import create_app


class TestFrontendBackendIntegration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        class TestConfig:
            TESTING = True
            SECRET_KEY = "test-only"
            SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
            SQLALCHEMY_TRACK_MODIFICATIONS = False
            UPLOAD_FOLDER = "test_uploads"
            SAVED_MODELS_FOLDER = "test_saved_models"

        cls.app = create_app(TestConfig)

    def setUp(self):
        self.client = self.app.test_client()

    def test_frontend_page_loads(self):
        response = self.client.get("/")
        try:
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.headers["Location"], "/login")
        finally:
            response.close()

    def test_login_page_loads(self):
        response = self.client.get("/login")
        try:
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"login-form", response.data)
        finally:
            response.close()

    def test_dashboard_file_is_protected(self):
        response = self.client.get("/index.html")
        try:
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.headers["Location"], "/login")
        finally:
            response.close()

    def test_backend_health_endpoint(self):
        response = self.client.get("/api/health")
        try:
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json["status"], "healthy")
        finally:
            response.close()

    def test_frontend_javascript_is_served(self):
        response = self.client.get("/js/app.js")
        try:
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"API_BASE", response.data)
        finally:
            response.close()


if __name__ == "__main__":
    unittest.main()
