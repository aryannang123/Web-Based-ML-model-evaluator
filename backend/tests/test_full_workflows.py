import time
import unittest
from io import BytesIO
from pathlib import Path
import tempfile

from sqlalchemy import inspect

from app import create_app
from config import Config
from database.db import db
from models.dataset import Dataset
from models.security import AuditEvent, UserSession
from models.dataset_version import DatasetVersion
from models.model import MLModel
from models.user import User
from routes.auth_utils import digest
from werkzeug.security import generate_password_hash


CLASSIFICATION_CSV = "value,kind,result\n" + "".join(
    f"{index},{'a' if index % 2 else 'b'},{'high' if index % 2 else 'low'}\n"
    for index in range(40)
)
REGRESSION_CSV = "x,y\n" + "".join(
    f"{index},{index * 3 + (index % 4)}\n" for index in range(40)
)


class TestFullWorkflows(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.storage = tempfile.TemporaryDirectory(
            prefix="ml-evaluator-workflows-", dir=Path(__file__).resolve().parent
        )
        root = Path(cls.storage.name)

        class TestConfig:
            TESTING = True
            SECRET_KEY = "workflow-test-secret"
            SESSION_COOKIE_HTTPONLY = True
            SESSION_COOKIE_SAMESITE = "Lax"
            SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
            SQLALCHEMY_TRACK_MODIFICATIONS = False
            UPLOAD_FOLDER = str(root / "uploads")
            SAVED_MODELS_FOLDER = str(root / "models")
            SESSION_IDLE_TIMEOUT_SECONDS = 600
            LOGIN_RATE_LIMIT_WINDOW_SECONDS = 900
            LOGIN_RATE_LIMIT_MAX_FAILURES = 3
            TRAIN_TEST_RANDOM_STATE = 42
            MAX_CONTENT_LENGTH = 16 * 1024 * 1024
            ALLOWED_EXTENSIONS = {"csv"}
            DATASET_PREVIEW_ROWS = 10
            PERMANENT_SESSION_LIFETIME = 12 * 60 * 60

        cls.app = create_app(TestConfig)

    @classmethod
    def tearDownClass(cls):
        with cls.app.app_context():
            db.session.remove()
            db.drop_all()
        cls.storage.cleanup()

    def setUp(self):
        with self.app.app_context():
            db.drop_all()
            db.create_all()
        self.client = self.app.test_client()
        self.student = self.make_user("student", "student")

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()

    def make_user(self, username, role="student", active=True):
        with self.app.app_context():
            user = User(
                username=username,
                email=f"{username}@example.org",
                password_hash=generate_password_hash("StrongPass123!"),
                role=role,
                is_active=active,
            )
            db.session.add(user)
            db.session.commit()
            return user.id

    def login(self, username="student", client=None):
        client = client or self.client
        response = client.post("/api/auth/login", json={
            "username": username, "password": "StrongPass123!"
        })
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        return response

    def upload(self, text=CLASSIFICATION_CSV, filename="sample.csv", client=None):
        client = client or self.client
        return client.post(
            "/api/dataset/upload",
            data={"file": (BytesIO(text.encode("utf-8")), filename)},
            content_type="multipart/form-data",
        )

    def train(self, dataset_id, target="result", algorithm="decision_tree",
              share=False, client=None, test_size=0.2):
        client = client or self.client
        return client.post("/api/ml/train", json={
            "dataset_id": dataset_id,
            "target_column": target,
            "algorithm": algorithm,
            "test_size": test_size,
            "share_with_instructors": share,
        })

    def test_registration_creates_student_and_never_accepts_elevated_role(self):
        response = self.client.post("/api/auth/register", json={
            "username": "new-student", "email": "new@example.org",
            "password": "StrongPass123!", "role": "admin",
        })
        self.assertEqual(response.status_code, 201)
        with self.app.app_context():
            user = User.query.filter_by(username="new-student").one()
            self.assertEqual(user.role, "student")
            self.assertNotEqual(user.password_hash, "StrongPass123!")

    def test_logout_revokes_replayed_session_and_page_access(self):
        self.login()
        cookie_name = self.app.config["SESSION_COOKIE_NAME"]
        cookie = self.client.get_cookie(cookie_name)
        with self.client.session_transaction() as session_data:
            raw_id = session_data["session_id"]
        response = self.client.post("/api/auth/logout")
        self.assertEqual(response.status_code, 200)
        self.client.set_cookie(cookie_name, cookie.value)
        self.assertEqual(self.client.get("/api/ml/runs").status_code, 401)
        self.assertEqual(self.client.get("/").status_code, 302)
        with self.app.app_context():
            self.assertIsNone(db.session.get(UserSession, digest(raw_id)))

    def test_idle_expired_session_is_rejected(self):
        self.login()
        with self.client.session_transaction() as session_data:
            raw_id = session_data["session_id"]
        with self.app.app_context():
            record = db.session.get(UserSession, digest(raw_id))
            record.last_activity = int(time.time()) - 700
            db.session.commit()
        self.assertEqual(self.client.get("/api/ml/runs").status_code, 401)

    def test_absolute_session_lifetime_is_limited_to_twelve_hours(self):
        self.login()
        with self.client.session_transaction() as session_data:
            raw_session_id = session_data["session_id"]
        with self.app.app_context():
            record = db.session.get(UserSession, digest(raw_session_id))
            self.assertIsNotNone(record)
            self.assertEqual(
                record.expires_at - record.created_at,
                12 * 60 * 60,
            )
            record.expires_at = int(time.time()) - 1
            db.session.commit()
        self.assertEqual(self.client.get("/api/ml/runs").status_code, 401)

    def test_upload_limit_returns_controlled_413(self):
        self.login()
        over_limit = b"x" * (Config.MAX_CONTENT_LENGTH + 1)
        response = self.client.post(
            "/api/dataset/upload",
            data={"file": (BytesIO(over_limit), "too-large.csv")},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 413)
        self.assertEqual(
            response.json["error"], "Upload exceeds the 16 MiB request limit"
        )

        dataset_id = self.upload().json["dataset"]["id"]
        replacement = self.client.put(
            f"/api/dataset/{dataset_id}/replace",
            data={"file": (BytesIO(over_limit), "too-large.csv")},
            content_type="multipart/form-data",
        )
        self.assertEqual(replacement.status_code, 413)
        self.assertEqual(
            self.client.get(f"/api/dataset/{dataset_id}").status_code, 200
        )

    def test_supported_algorithms_are_task_specific_and_match_policy(self):
        self.login()
        response = self.client.get("/api/ml/algorithms")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json,
            {
                "classification": [
                    "logistic_regression", "decision_tree", "random_forest", "knn"
                ],
                "regression": [
                    "linear_regression", "decision_tree", "random_forest", "knn"
                ],
            },
        )

    def test_us02_schema_has_required_entities_and_relationships(self):
        with self.app.app_context():
            schema = inspect(db.engine)
            tables = set(schema.get_table_names())
            self.assertTrue({
                "users", "datasets", "dataset_versions", "models",
                "evaluation_results", "user_sessions",
            }.issubset(tables))
            for table_name, expected in {
                "datasets": {"user_id": "users"},
                "models": {"user_id": "users", "dataset_id": "datasets"},
                "evaluation_results": {"user_id": "users", "model_id": "models"},
            }.items():
                foreign_keys = schema.get_foreign_keys(table_name)
                actual = {
                    column: target_table
                    for foreign_key in foreign_keys
                    for column, target_table in zip(
                        foreign_key["constrained_columns"],
                        [foreign_key["referred_table"]] * len(
                            foreign_key["constrained_columns"]
                        ),
                    )
                }
                self.assertTrue(expected.items() <= actual.items(), table_name)

    def test_login_throttle_blocks_repeated_failures_and_logs_them_safely(self):
        for _ in range(3):
            response = self.client.post("/api/auth/login", json={
                "username": "student", "password": "bad-password"
            })
            self.assertEqual(response.status_code, 401)
        blocked = self.client.post("/api/auth/login", json={
            "username": "student", "password": "bad-password"
        })
        self.assertEqual(blocked.status_code, 429)
        with self.app.app_context():
            events = {row.event_type for row in AuditEvent.query.all()}
            self.assertIn("auth.login_failed", events)
            self.assertIn("auth.login_throttled", events)
            for event in AuditEvent.query.all():
                self.assertNotIn("password", str(event.details_json).lower())

    def test_dataset_upload_metadata_preview_statistics_and_preprocessing(self):
        self.login()
        upload = self.upload()
        self.assertEqual(upload.status_code, 201, upload.get_data(as_text=True))
        dataset = upload.json["dataset"]
        self.assertEqual(dataset["row_count"], 40)
        self.assertEqual(dataset["column_count"], 3)
        self.assertEqual(dataset["metadata"]["encoding"], "UTF-8")
        self.assertEqual(dataset["version"], 1)
        preview = self.client.get(f"/api/dataset/{dataset['id']}/preview")
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(len(preview.json["rows"]), 10)
        stats = self.client.get(f"/api/dataset/{dataset['id']}/statistics")
        self.assertEqual(stats.status_code, 200, stats.get_data(as_text=True))
        self.assertEqual(stats.json["row_count"], 40)
        options = {"missing_strategy": "drop_rows", "numeric_imputer": "mean",
                   "encode_categorical": True, "scale_numeric": False}
        saved = self.client.post(
            f"/api/dataset/{dataset['id']}/preprocess", json=options
        )
        self.assertEqual(saved.status_code, 200)
        target = self.client.post(f"/api/dataset/{dataset['id']}/target",
                                  json={"target_column": "result"})
        self.assertEqual(target.status_code, 200)
        self.assertEqual(target.json["task_type"], "classification")
        self.assertIn("logistic_regression", target.json["algorithms"])

    def test_invalid_csv_and_extension_are_rejected(self):
        self.login()
        for content, name in [("", "empty.csv"), ("a,b\n1\n2,3,4", "bad.csv"),
                              (CLASSIFICATION_CSV, "data.txt"),
                              ("a,a\n1,2\n3,4", "duplicate.csv")]:
            response = self.upload(content, name)
            self.assertEqual(response.status_code, 400, response.get_data(as_text=True))
        listing = self.client.get("/api/dataset")
        self.assertEqual(listing.json["datasets"], [])

    def test_replacement_validation_failure_keeps_old_dataset_intact(self):
        self.login()
        dataset_id = self.upload().json["dataset"]["id"]
        failure = self.client.put(
            f"/api/dataset/{dataset_id}/replace",
            data={"file": (BytesIO(b"bad"), "bad.csv")},
            content_type="multipart/form-data",
        )
        self.assertEqual(failure.status_code, 400)
        preview = self.client.get(f"/api/dataset/{dataset_id}/preview")
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview.json["columns"], ["value", "kind", "result"])

    def test_successful_replacement_preserves_old_dataset_version_for_run_history(self):
        self.login()
        dataset_id = self.upload(filename="original.csv").json["dataset"]["id"]
        run_response = self.train(dataset_id)
        self.assertEqual(run_response.status_code, 201)
        run_id = run_response.json["run"]["id"]
        with self.app.app_context():
            run = db.session.get(MLModel, run_id)
            old_version_id = run.dataset_version_id
            old_version_path = db.session.get(DatasetVersion, old_version_id).file_path

        replacement_text = "feature,target\n" + "".join(
            f"{i},{'yes' if i % 2 else 'no'}\n" for i in range(40)
        )
        response = self.client.put(
            f"/api/dataset/{dataset_id}/replace",
            data={"file": (BytesIO(replacement_text.encode()), "replacement.csv")},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        self.assertEqual(response.json["dataset"]["version"], 2)
        self.assertTrue(Path(old_version_path).is_file())
        history = self.client.get(f"/api/ml/runs/{run_id}").json["run"]
        self.assertEqual(history["dataset_name"], "original.csv")
        self.assertEqual(history["dataset_version"], 1)
        with self.app.app_context():
            self.assertEqual(
                DatasetVersion.query.filter_by(dataset_id=dataset_id).count(), 2
            )

    def test_admin_deactivation_revokes_existing_user_session(self):
        self.login()
        student_id = self.student
        admin_id = self.make_user("deactivate-admin", "admin")
        admin = self.app.test_client()
        self.login("deactivate-admin", admin)
        response = admin.patch(f"/api/admin/users/{student_id}", json={
            "role": "student", "is_active": False
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/api/ml/runs").status_code, 401)
        self.assertEqual(admin.get("/api/admin/users").status_code, 200)
        self.assertIsNotNone(admin_id)

    def test_local_cli_can_promote_registered_user_to_admin(self):
        self.make_user("cli-admin")
        result = self.app.test_cli_runner().invoke(
            args=["promote-admin", "cli-admin"]
        )
        self.assertEqual(result.exit_code, 0, result.output)
        with self.app.app_context():
            self.assertEqual(User.query.filter_by(username="cli-admin").one().role,
                             "admin")

    def test_dataset_and_run_ids_are_owner_scoped(self):
        self.login()
        dataset_id = self.upload().json["dataset"]["id"]
        run_id = self.train(dataset_id).json["run"]["id"]
        other_id = self.make_user("other")
        other_client = self.app.test_client()
        self.login("other", other_client)
        self.assertEqual(other_client.get(f"/api/dataset/{dataset_id}").status_code, 404)
        self.assertEqual(other_client.get(f"/api/ml/runs/{run_id}").status_code, 404)
        self.assertEqual(other_client.get("/api/ml/runs").json["runs"], [])

    def test_classification_training_history_comparison_and_exports(self):
        self.login()
        dataset_id = self.upload().json["dataset"]["id"]
        first = self.train(dataset_id)
        self.assertEqual(first.status_code, 201, first.get_data(as_text=True))
        self.assertEqual(first.json["run"]["status"], "completed")
        self.assertIn("accuracy", first.json["run"]["metrics"])
        second = self.train(dataset_id, algorithm="random_forest")
        self.assertEqual(second.status_code, 201, second.get_data(as_text=True))
        ids = [first.json["run"]["id"], second.json["run"]["id"]]
        compare = self.client.post("/api/ml/compare", json={"run_ids": ids})
        self.assertEqual(compare.status_code, 200)
        self.assertEqual(len(compare.json["runs"]), 2)
        self.assertEqual(len(self.client.get("/api/ml/runs").json["runs"]), 2)
        model_download = self.client.get(
            f"/api/ml/runs/{ids[0]}/download/model")
        self.assertEqual(model_download.status_code, 200)
        model_download.close()
        report = self.client.get(f"/api/ml/runs/{ids[0]}/download/report")
        self.assertEqual(report.status_code, 200)
        self.assertIn(b"confusion_matrix", report.data)
        report.close()

    def test_regression_training_calculates_regression_metrics(self):
        self.login()
        dataset_id = self.upload(REGRESSION_CSV, "regression.csv").json["dataset"]["id"]
        target = self.client.post(f"/api/dataset/{dataset_id}/target",
                                  json={"target_column": "y"})
        self.assertEqual(target.json["task_type"], "regression")
        response = self.train(dataset_id, target="y", algorithm="linear_regression")
        self.assertEqual(response.status_code, 201, response.get_data(as_text=True))
        metrics = response.json["run"]["metrics"]
        self.assertTrue({"mae", "mse", "rmse", "r2"}.issubset(metrics))

    def test_invalid_target_and_incompatible_algorithm_are_rejected(self):
        self.login()
        dataset_id = self.upload().json["dataset"]["id"]
        bad_target = self.train(dataset_id, target="missing")
        self.assertEqual(bad_target.status_code, 400)
        bad_algorithm = self.train(dataset_id, algorithm="linear_regression")
        self.assertEqual(bad_algorithm.status_code, 400)

    def test_comparison_rejects_incompatible_and_foreign_runs(self):
        self.login()
        first_dataset = self.upload().json["dataset"]["id"]
        run_one = self.train(first_dataset).json["run"]["id"]
        second_dataset = self.upload(filename="second.csv").json["dataset"]["id"]
        run_two = self.train(second_dataset).json["run"]["id"]
        incompatible = self.client.post("/api/ml/compare", json={
            "run_ids": [run_one, run_two]
        })
        self.assertEqual(incompatible.status_code, 400)
        self.assertEqual(self.client.post("/api/ml/compare", json={
            "run_ids": [run_one, 999999]
        }).status_code, 404)

    def test_instructor_sees_only_published_results_and_cannot_write(self):
        self.login()
        dataset_id = self.upload().json["dataset"]["id"]
        private_run = self.train(dataset_id).json["run"]["id"]
        shared = self.train(dataset_id, algorithm="random_forest", share=True)
        shared_run = shared.json["run"]["id"]
        instructor_id = self.make_user("teacher", "instructor")
        instructor = self.app.test_client()
        self.login("teacher", instructor)
        response = instructor.get("/api/instructor/results")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["id"] for row in response.json["results"]], [shared_run])
        self.assertEqual(instructor.get(f"/api/instructor/results/{private_run}").status_code, 404)
        self.assertEqual(instructor.post("/api/ml/train", json={}).status_code, 403)
        self.assertEqual(instructor.patch(f"/api/ml/runs/{shared_run}/share",
                                          json={"shared": False}).status_code, 403)
        self.assertIsNotNone(instructor_id)

    def test_owner_can_revoke_instructor_sharing(self):
        self.login()
        dataset_id = self.upload().json["dataset"]["id"]
        run_id = self.train(dataset_id, share=True).json["run"]["id"]
        response = self.client.patch(f"/api/ml/runs/{run_id}/share",
                                     json={"shared": False})
        self.assertEqual(response.status_code, 200)
        instructor_id = self.make_user("reader", "instructor")
        instructor = self.app.test_client()
        self.login("reader", instructor)
        self.assertEqual(instructor.get("/api/instructor/results").json["results"], [])
        self.assertIsNotNone(instructor_id)

    def test_admin_user_management_dataset_archiving_and_audit_are_protected(self):
        self.login()
        dataset_id = self.upload().json["dataset"]["id"]
        regular_id = self.make_user("regular")
        admin_id = self.make_user("admin", "admin")
        self.assertEqual(self.client.get("/api/admin/users").status_code, 403)
        admin = self.app.test_client()
        self.login("admin", admin)
        self.assertEqual(admin.get("/api/admin/users").status_code, 200)
        update = admin.patch(f"/api/admin/users/{regular_id}", json={
            "role": "instructor", "is_active": True
        })
        self.assertEqual(update.status_code, 200)
        datasets = admin.get("/api/admin/datasets").json["datasets"]
        self.assertTrue(any(row["id"] == dataset_id for row in datasets))
        archive = admin.patch(f"/api/admin/datasets/{dataset_id}", json={
            "is_archived": True
        })
        self.assertEqual(archive.status_code, 200)
        self.assertEqual(admin.get("/api/admin/logs").status_code, 200)
        self.assertEqual(admin.post("/api/admin/logs").status_code, 405)
        with self.app.app_context():
            self.assertEqual(db.session.get(User, regular_id).role, "instructor")
            self.assertTrue(db.session.get(Dataset, dataset_id).is_archived)
            self.assertIsNotNone(db.session.get(User, admin_id))

    def test_only_cli_or_admin_can_grant_roles_and_last_admin_cannot_be_removed(self):
        admin_id = self.make_user("sole-admin", "admin")
        self.login("sole-admin")
        response = self.client.patch(f"/api/admin/users/{admin_id}", json={
            "role": "student", "is_active": True
        })
        self.assertEqual(response.status_code, 400)
        register = self.client.post("/api/auth/register", json={
            "username": "untrusted-role", "email": "role@example.org",
            "password": "StrongPass123!", "role": "admin",
        })
        self.assertEqual(register.status_code, 201)
        with self.app.app_context():
            self.assertEqual(User.query.filter_by(username="untrusted-role").one().role,
                             "student")

    def test_role_pages_and_direct_html_files_are_authorized(self):
        self.assertEqual(self.client.get("/admin").status_code, 302)
        self.login()
        self.assertEqual(self.client.get("/admin.html").status_code, 302)
        self.assertEqual(self.client.get("/instructor.html").status_code, 302)
        self.make_user("page-admin", "admin")
        admin = self.app.test_client()
        self.login("page-admin", admin)
        admin_page = admin.get("/admin")
        self.assertEqual(admin_page.status_code, 200)
        admin_page.close()
        self.assertEqual(admin.get("/instructor").status_code, 302)


if __name__ == "__main__":
    unittest.main()
