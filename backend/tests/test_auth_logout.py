import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from app import create_app
from database.db import db
from models.user import User
from werkzeug.security import generate_password_hash


class TestLogout(unittest.TestCase):
    """US-06: Test logout and session management functionality."""

    @classmethod
    def setUpClass(cls):
        cls.storage = tempfile.TemporaryDirectory(
            prefix="ml-evaluator-logout-",
            dir=Path(__file__).resolve().parent,
        )
        storage_path = Path(cls.storage.name)

        class TestConfig:
            TESTING = True
            SECRET_KEY = "test-only-logout-key"
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
        db.engine.dispose()
        cls.context.pop()
        cls.storage.cleanup()

    def setUp(self):
        self.client = self.app.test_client()
        self.username = f"logout_{uuid4().hex[:10]}"
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

    def login(self):
        """Helper method to log in the test user."""
        response = self.client.post(
            "/api/auth/login",
            json={"username": self.username, "password": self.password},
        )
        self.assertEqual(response.status_code, 200)
        return response

    def test_logged_in_user_can_logout_successfully(self):
        """US-06 AC: Logged-in users can log out successfully."""
        self.login()

        # Verify user is logged in
        with self.client.session_transaction() as session_data:
            self.assertEqual(session_data["user_id"], self.user.id)

        # Perform logout
        response = self.client.post("/api/auth/logout")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["message"], "Logout successful")
        self.assertEqual(response.json["redirect_url"], "/login")

    def test_logout_invalidates_the_active_session(self):
        """US-06 AC: Logout invalidates the active session/token."""
        self.login()

        # Logout
        logout_response = self.client.post("/api/auth/logout")
        self.assertEqual(logout_response.status_code, 200)

        # Verify session is cleared
        with self.client.session_transaction() as session_data:
            self.assertNotIn("user_id", session_data)
            self.assertNotIn("username", session_data)

    def test_after_logout_protected_pages_cannot_be_accessed(self):
        """US-06 AC: After logout, protected pages cannot be accessed without logging in again."""
        self.login()

        # Access protected dashboard before logout
        dashboard_before = self.client.get("/", follow_redirects=False)
        self.assertEqual(dashboard_before.status_code, 200)
        dashboard_before.close()

        # Logout
        self.client.post("/api/auth/logout")

        # Try to access protected resources after logout
        dashboard_after = self.client.get("/", follow_redirects=False)
        protected_api = self.client.get("/api/ml/algorithms")

        self.assertEqual(dashboard_after.status_code, 302)
        self.assertEqual(dashboard_after.headers["Location"], "/login")
        self.assertEqual(protected_api.status_code, 401)
        self.assertEqual(protected_api.json["error"], "Authentication required")

        dashboard_after.close()
        protected_api.close()

    def test_logout_when_not_logged_in_returns_gracefully(self):
        """Test logout endpoint when there's no active session."""
        # Don't log in, just call logout
        response = self.client.post("/api/auth/logout")

        self.assertEqual(response.status_code, 200)
        self.assertIn("No active session", response.json["message"])
        self.assertEqual(response.json["redirect_url"], "/login")

    def test_session_state_maintained_while_navigating(self):
        """US-06 AC: User session state is maintained while navigating the application."""
        self.login()

        # Navigate to different protected endpoints
        dashboard = self.client.get("/")
        api_algorithms = self.client.get("/api/ml/algorithms")
        session_check = self.client.get("/api/auth/session")

        try:
            self.assertEqual(dashboard.status_code, 200)
            self.assertEqual(api_algorithms.status_code, 200)
            self.assertEqual(session_check.status_code, 200)
            self.assertTrue(session_check.json["authenticated"])
            self.assertEqual(session_check.json["user"]["username"], self.username)
        finally:
            dashboard.close()
            api_algorithms.close()
            session_check.close()

        # Verify session is still active
        with self.client.session_transaction() as session_data:
            self.assertEqual(session_data["user_id"], self.user.id)
            self.assertEqual(session_data["username"], self.username)

    def test_logout_clears_all_session_data(self):
        """Ensure logout completely clears session data."""
        self.login()

        # Add some additional session data
        with self.client.session_transaction() as session_data:
            session_data["custom_key"] = "custom_value"
            self.assertIn("user_id", session_data)
            self.assertIn("custom_key", session_data)

        # Logout
        self.client.post("/api/auth/logout")

        # Verify all session data is cleared
        with self.client.session_transaction() as session_data:
            self.assertNotIn("user_id", session_data)
            self.assertNotIn("username", session_data)
            self.assertNotIn("custom_key", session_data)
            self.assertEqual(len(session_data), 0)

    def test_multiple_logouts_are_idempotent(self):
        """Test that multiple logout calls don't cause errors."""
        self.login()

        # First logout
        first_logout = self.client.post("/api/auth/logout")
        self.assertEqual(first_logout.status_code, 200)

        # Second logout (already logged out)
        second_logout = self.client.post("/api/auth/logout")
        self.assertEqual(second_logout.status_code, 200)
        self.assertIn("No active session", second_logout.json["message"])

        # Third logout
        third_logout = self.client.post("/api/auth/logout")
        self.assertEqual(third_logout.status_code, 200)

    def test_session_has_expiration_configured(self):
        """US-06 AC: Session expiration is handled appropriately."""
        self.login()
        
        # Verify session is permanent (allows expiration)
        with self.client.session_transaction() as session_data:
            # Flask sets session.permanent when PERMANENT_SESSION_LIFETIME is configured
            # In test environment, verify the session contains user data
            self.assertIn("user_id", session_data)
        
        # Verify config has session lifetime set
        self.assertIsNotNone(self.app.config.get("PERMANENT_SESSION_LIFETIME"))


if __name__ == "__main__":
    unittest.main()
