import io
import json
import os
import tempfile
import unittest

from werkzeug.security import generate_password_hash

from app import create_app
from database.db import db
from models.activity_log import ActivityLog
from models.dataset import Dataset
from models.user import User


class TestUS14aRBACAndAdmin(unittest.TestCase):
    """Test suite for US-14a: Role-Based Access Control and Admin Management.

    Verifies FR-7.1, FR-7.2, FR-7.3, and FR-7.5 test cases defined in Section 13
    of the Test Plan Document.
    """

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_us14a.db")

        test_config = {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{self.db_path}",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "SECRET_KEY": "test-secret-key",
            "UPLOAD_FOLDER": os.path.join(self.temp_dir, "uploads"),
            "SAVED_MODELS_FOLDER": os.path.join(self.temp_dir, "models"),
            "WTF_CSRF_ENABLED": False,
        }

        self.app = create_app(type("TestConfig", (), test_config))
        self.client = self.app.test_client()

        with self.app.app_context():
            db.create_all()

            # Create standard test accounts:
            # 1. Admin user
            self.admin = User(
                username="admin_user",
                email="admin@example.com",
                password_hash=generate_password_hash("AdminPass123"),
                role="admin",
                is_active=True
            )
            # 2. Student user (User A)
            self.student = User(
                username="student_user",
                email="student@example.com",
                password_hash=generate_password_hash("StudentPass123"),
                role="student",
                is_active=True
            )
            # 3. Instructor user
            self.instructor = User(
                username="instructor_user",
                email="instructor@example.com",
                password_hash=generate_password_hash("InstructorPass123"),
                role="instructor",
                is_active=True
            )
            # 4. Inactive user
            self.inactive_user = User(
                username="inactive_user",
                email="inactive@example.com",
                password_hash=generate_password_hash("InactivePass123"),
                role="student",
                is_active=False
            )

            db.session.add_all([self.admin, self.student, self.instructor, self.inactive_user])
            db.session.commit()

            # Seed a dataset for Student
            self.dataset = Dataset(
                user_id=self.student.id,
                filename="student_data.csv",
                file_path=os.path.join(self.temp_dir, "student_data.csv"),
                file_size=1024,
                row_count=100,
                column_count=5,
                metadata_json={"columns": ["f1", "f2", "f3", "f4", "target"]},
            )
            db.session.add(self.dataset)
            db.session.commit()

            self.admin_id = self.admin.id
            self.student_id = self.student.id
            self.instructor_id = self.instructor.id
            self.dataset_id = self.dataset.id

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

        for root, dirs, files in os.walk(self.temp_dir, topdown=False):
            for file in files:
                try:
                    os.remove(os.path.join(root, file))
                except OSError:
                    pass
            for d in dirs:
                try:
                    os.rmdir(os.path.join(root, d))
                except OSError:
                    pass
        try:
            os.rmdir(self.temp_dir)
        except OSError:
            pass

    def _login(self, username, password):
        """Helper to authenticate and store session cookies."""
        return self.client.post(
            "/api/auth/login",
            data=json.dumps({"username": username, "password": password}),
            content_type="application/json",
        )

    # ─── FR-7.5: ROLE-BASED ACCESS CONTROL FOUNDATION ─────────────────────────

    def test_fr7_5_it_1_newly_registered_users_assigned_student_role_by_default(self):
        """FR-7.5-IT-1: Verify new user registration always assigns the Student role."""
        payload = {
            "username": "new_candidate",
            "email": "candidate@example.com",
            "password": "ValidPassword123",
            "role": "admin"  # Attempt privilege escalation
        }
        res = self.client.post("/api/auth/register", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data["role"], "student")

        with self.app.app_context():
            user = User.query.filter_by(username="new_candidate").first()
            self.assertIsNotNone(user)
            self.assertEqual(user.role, "student")
            self.assertTrue(user.is_active)

    def test_fr7_5_st_1_cross_role_access_control_enforced_server_side(self):
        """FR-7.5-ST-1: Verify server-side role enforcement blocks student & instructor from admin endpoints."""
        # Unauthenticated request -> 401
        res = self.client.get("/api/admin/users")
        self.assertEqual(res.status_code, 401)

        # Student login -> attempts admin endpoint -> 403
        self._login("student_user", "StudentPass123")
        res = self.client.get("/api/admin/users")
        self.assertEqual(res.status_code, 403)
        self.assertIn("insufficient permissions", res.get_json()["error"])

        # Instructor login -> attempts admin endpoint -> 403
        self._login("instructor_user", "InstructorPass123")
        res = self.client.get("/api/admin/users")
        self.assertEqual(res.status_code, 403)

        # Deactivated user login blocked -> 403
        res = self._login("inactive_user", "InactivePass123")
        self.assertEqual(res.status_code, 403)

    # ─── FR-7.1: ADMIN USER MANAGEMENT ────────────────────────────────────────

    def test_fr7_1_st_1_admin_can_view_registered_users_list(self):
        """FR-7.1-ST-1: Verify admin can view all registered platform accounts."""
        self._login("admin_user", "AdminPass123")
        res = self.client.get("/api/admin/users")
        self.assertEqual(res.status_code, 200)

        data = res.get_json()
        self.assertIn("users", data)
        self.assertGreaterEqual(len(data["users"]), 4)

        usernames = [u["username"] for u in data["users"]]
        self.assertIn("admin_user", usernames)
        self.assertIn("student_user", usernames)
        self.assertIn("instructor_user", usernames)

    def test_fr7_1_st_2_admin_can_perform_supported_account_management_action(self):
        """FR-7.1-ST-2: Verify admin can view details and toggle user active status."""
        self._login("admin_user", "AdminPass123")

        # 1. View single user
        res = self.client.get(f"/api/admin/users/{self.student_id}")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["user"]["username"], "student_user")

        # 2. Deactivate student account
        res = self.client.patch(
            f"/api/admin/users/{self.student_id}",
            data=json.dumps({"is_active": False}),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.get_json()["user"]["is_active"])

        # 3. Confirm deactivated user cannot log in
        self.client.post("/api/auth/logout")
        res = self._login("student_user", "StudentPass123")
        self.assertEqual(res.status_code, 403)

        # 4. Reactivate account
        self._login("admin_user", "AdminPass123")
        res = self.client.patch(
            f"/api/admin/users/{self.student_id}",
            data=json.dumps({"is_active": True}),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()["user"]["is_active"])

    def test_fr7_1_st_3_non_admin_cannot_access_or_call_user_management(self):
        """FR-7.1-ST-3: Verify non-admin (Student/Instructor) direct calls are denied."""
        # Student
        self._login("student_user", "StudentPass123")
        self.assertEqual(self.client.get("/api/admin/users").status_code, 403)
        self.assertEqual(self.client.get(f"/api/admin/users/{self.student_id}").status_code, 403)
        self.assertEqual(self.client.patch(f"/api/admin/users/{self.student_id}", data=json.dumps({"is_active": False}), content_type="application/json").status_code, 403)

        # Instructor
        self._login("instructor_user", "InstructorPass123")
        self.assertEqual(self.client.get("/api/admin/users").status_code, 403)

    # ─── FR-7.2: ADMIN DATASET OVERSIGHT ──────────────────────────────────────

    def test_fr7_2_st_1_admin_can_view_stored_dataset_records_and_metadata(self):
        """FR-7.2-ST-1: Verify admin can view dataset records and metadata across accounts."""
        self._login("admin_user", "AdminPass123")
        res = self.client.get("/api/admin/datasets")
        self.assertEqual(res.status_code, 200)

        data = res.get_json()
        self.assertIn("datasets", data)
        self.assertGreaterEqual(len(data["datasets"]), 1)

        d = data["datasets"][0]
        self.assertEqual(d["filename"], "student_data.csv")
        self.assertEqual(d["owner_username"], "student_user")
        self.assertEqual(d["row_count"], 100)
        self.assertEqual(d["column_count"], 5)

    def test_fr7_2_st_2_dataset_management_preserves_ownership_associations(self):
        """FR-7.2-ST-2: Verify dataset management preserves dataset user_id ownership."""
        self._login("admin_user", "AdminPass123")
        res = self.client.get(f"/api/admin/datasets/{self.dataset_id}")
        self.assertEqual(res.status_code, 200)
        d = res.get_json()["dataset"]
        self.assertEqual(d["user_id"], self.student_id)
        self.assertEqual(d["owner_username"], "student_user")

        # Deleting a dataset through admin endpoint
        res = self.client.delete(f"/api/admin/datasets/{self.dataset_id}")
        self.assertEqual(res.status_code, 200)

        # Confirm dataset is deleted
        with self.app.app_context():
            self.assertIsNone(db.session.get(Dataset, self.dataset_id))

    def test_fr7_2_st_3_non_admin_cannot_access_administrative_dataset_management(self):
        """FR-7.2-ST-3: Verify non-admin (Student/Instructor) cannot call admin dataset endpoints."""
        self._login("student_user", "StudentPass123")
        self.assertEqual(self.client.get("/api/admin/datasets").status_code, 403)
        self.assertEqual(self.client.delete(f"/api/admin/datasets/{self.dataset_id}").status_code, 403)

        self._login("instructor_user", "InstructorPass123")
        self.assertEqual(self.client.get("/api/admin/datasets").status_code, 403)

    # ─── FR-7.3: SYSTEM ACTIVITY LOGS ─────────────────────────────────────────

    def test_fr7_3_st_1_admin_can_view_application_activity_logs(self):
        """FR-7.3-ST-1: Verify admin can view recorded system activity logs."""
        self._login("admin_user", "AdminPass123")
        res = self.client.get("/api/admin/logs")
        self.assertEqual(res.status_code, 200)

        data = res.get_json()
        self.assertIn("logs", data)
        self.assertGreaterEqual(len(data["logs"]), 1)

        actions = [log["action"] for log in data["logs"]]
        self.assertIn("USER_LOGIN", actions)

    def test_fr7_3_st_2_activity_logs_are_read_only_and_mask_secrets(self):
        """FR-7.3-ST-2: Verify logs are read-only and never expose sensitive passwords or tokens."""
        self._login("admin_user", "AdminPass123")

        # Mutating endpoints on /logs are disallowed (405 Method Not Allowed)
        self.assertEqual(self.client.post("/api/admin/logs", data=json.dumps({"action": "FAKE"}), content_type="application/json").status_code, 405)
        self.assertEqual(self.client.delete("/api/admin/logs").status_code, 405)

        # Inspect logged entries for credentials
        res = self.client.get("/api/admin/logs")
        self.assertEqual(res.status_code, 200)
        logs_str = json.dumps(res.get_json()["logs"])

        # Passwords and session secrets must never appear in log contents
        self.assertNotIn("AdminPass123", logs_str)
        self.assertNotIn("StudentPass123", logs_str)
        self.assertNotIn("password_hash", logs_str)

    def test_fr7_3_st_3_non_admin_cannot_access_system_log_interface(self):
        """FR-7.3-ST-3: Verify non-admin and Instructor cannot call activity log API."""
        self._login("student_user", "StudentPass123")
        self.assertEqual(self.client.get("/api/admin/logs").status_code, 403)

        self._login("instructor_user", "InstructorPass123")
        self.assertEqual(self.client.get("/api/admin/logs").status_code, 403)


if __name__ == "__main__":
    unittest.main()
