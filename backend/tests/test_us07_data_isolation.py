import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

from app import create_app
from database.db import db
from models.dataset import Dataset
from models.evaluation import EvaluationResult
from models.model import MLModel
from models.user import User
from werkzeug.security import generate_password_hash
from sqlalchemy.exc import IntegrityError


class TestUserDataIsolation(unittest.TestCase):
    """US-07 owner isolation tests mapped to the committed Test Plan IDs."""

    @classmethod
    def setUpClass(cls):
        cls.storage = tempfile.TemporaryDirectory(
            prefix="ml-evaluator-isolation-",
            dir=Path(__file__).resolve().parent,
        )
        storage_path = Path(cls.storage.name)

        class TestConfig:
            TESTING = True
            SECRET_KEY = "test-only-isolation-key"
            SESSION_COOKIE_HTTPONLY = True
            SESSION_COOKIE_SAMESITE = "Lax"
            PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
            SESSION_REFRESH_EACH_REQUEST = True
            SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
            SQLALCHEMY_TRACK_MODIFICATIONS = False
            UPLOAD_FOLDER = str(storage_path / "uploads")
            SAVED_MODELS_FOLDER = str(storage_path / "models")

        cls.app = create_app(TestConfig)
        cls.context = cls.app.app_context()
        cls.context.push()
        db.create_all()

        suffix = uuid4().hex[:10]
        cls.user_a = User(
            username=f"owner_a_{suffix}",
            email=f"owner_a_{suffix}@example.com",
            password_hash=generate_password_hash("StrongPass123!"),
        )
        cls.user_b = User(
            username=f"owner_b_{suffix}",
            email=f"owner_b_{suffix}@example.com",
            password_hash=generate_password_hash("StrongPass123!"),
        )
        db.session.add_all([cls.user_a, cls.user_b])
        db.session.flush()

        cls.dataset_a = Dataset(
            user_id=cls.user_a.id,
            filename="owner-a.csv",
            file_path=str(storage_path / "owner-a.csv"),
            file_size=128,
            row_count=5,
            column_count=2,
            metadata_json={"columns": ["feature", "target"]},
        )
        cls.dataset_b = Dataset(
            user_id=cls.user_b.id,
            filename="owner-b.csv",
            file_path=str(storage_path / "owner-b.csv"),
            file_size=256,
            row_count=8,
            column_count=3,
            metadata_json={"columns": ["x", "y", "target"]},
        )
        db.session.add_all([cls.dataset_a, cls.dataset_b])
        db.session.flush()

        cls.model_a = MLModel(
            user_id=cls.user_a.id,
            dataset_id=cls.dataset_a.id,
            model_name="Owner A run",
            algorithm="random_forest",
            model_path=str(storage_path / "owner-a-model.pkl"),
            status="completed",
            config_json={"target": "target", "split": 0.2},
        )
        cls.model_b = MLModel(
            user_id=cls.user_b.id,
            dataset_id=cls.dataset_b.id,
            model_name="Owner B run",
            algorithm="linear_regression",
            model_path=str(storage_path / "owner-b-model.pkl"),
            status="completed",
            config_json={"target": "target", "split": 0.25},
        )
        # Invalid cross-owner associations are seeded as a defense-in-depth case.
        cls.mismatched_model = MLModel(
            user_id=cls.user_a.id,
            dataset_id=cls.dataset_b.id,
            model_name="Mismatched run",
            algorithm="random_forest",
            status="completed",
        )
        db.session.add_all([cls.model_a, cls.model_b, cls.mismatched_model])
        db.session.flush()

        cls.evaluation_a = EvaluationResult(
            user_id=cls.user_a.id,
            model_id=cls.model_a.id,
            metrics_json={"accuracy": 0.9},
            report_json={"summary": "owner-a-report"},
        )
        cls.evaluation_b = EvaluationResult(
            user_id=cls.user_b.id,
            model_id=cls.model_b.id,
            metrics_json={"r2": 0.8},
            report_json={"summary": "owner-b-report"},
        )
        db.session.add_all([cls.evaluation_a, cls.evaluation_b])
        db.session.commit()

    @classmethod
    def tearDownClass(cls):
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        cls.context.pop()
        cls.storage.cleanup()

    def setUp(self):
        self.client_a = self.app.test_client()
        self.client_b = self.app.test_client()
        self._login(self.client_a, self.user_a)
        self._login(self.client_b, self.user_b)

    def tearDown(self):
        self.client_a.post("/api/auth/logout")
        self.client_b.post("/api/auth/logout")

    @staticmethod
    def _login(client, user):
        response = client.post(
            "/api/auth/login",
            json={"username": user.username, "password": "StrongPass123!"},
        )
        if response.status_code != 200:
            raise AssertionError(f"Fixture login failed: {response.status_code}")

    def test_fr_2_5_st_2_each_user_lists_only_their_dataset_metadata(self):
        """FR-2.5-ST-2: Dataset listing and metadata remain isolated by owner."""
        datasets_a = self.client_a.get("/api/dataset")
        datasets_b = self.client_b.get("/api/dataset")
        self.assertEqual(datasets_a.status_code, 200)
        self.assertEqual(datasets_b.status_code, 200)
        self.assertEqual(
            [item["id"] for item in datasets_a.json["datasets"]],
            [self.dataset_a.id],
        )
        self.assertEqual(
            [item["id"] for item in datasets_b.json["datasets"]],
            [self.dataset_b.id],
        )

        own = self.client_a.get(f"/api/dataset/{self.dataset_a.id}")
        foreign = self.client_a.get(f"/api/dataset/{self.dataset_b.id}")
        self.assertEqual(own.status_code, 200)
        self.assertEqual(own.json["dataset"]["filename"], "owner-a.csv")
        self.assertNotIn("file_path", own.json["dataset"])
        self.assertEqual(foreign.status_code, 404)
        self.assertEqual(foreign.json, {"error": "Dataset not found"})

    def test_sec_az_2_st_1_foreign_dataset_model_and_evaluation_ids_are_denied(self):
        """SEC-AZ-2-ST-1: Direct IDs cannot retrieve another owner's records."""
        paths = [
            f"/api/dataset/{self.dataset_b.id}",
            f"/api/dataset/{self.dataset_b.id}/preview",
            f"/api/dataset/{self.dataset_b.id}/statistics",
            f"/api/ml/models/{self.model_b.id}",
            f"/api/ml/evaluations/{self.evaluation_b.id}",
        ]
        for path in paths:
            with self.subTest(path=path):
                response = self.client_a.get(path)
                self.assertEqual(response.status_code, 404)
                self.assertNotIn("owner-b", response.get_data(as_text=True))

    def test_fr_6_1_st_2_run_and_evaluation_history_is_private(self):
        """FR-6.1-ST-2: Each account sees and retrieves only its own run/results."""
        models_a = self.client_a.get("/api/ml/models")
        models_b = self.client_b.get("/api/ml/models")
        evaluations_a = self.client_a.get("/api/ml/evaluations")
        evaluations_b = self.client_b.get("/api/ml/evaluations")

        self.assertEqual([m["id"] for m in models_a.json["models"]], [self.model_a.id])
        self.assertEqual([m["id"] for m in models_b.json["models"]], [self.model_b.id])
        self.assertEqual(
            [e["id"] for e in evaluations_a.json["evaluations"]],
            [self.evaluation_a.id],
        )
        self.assertEqual(
            [e["id"] for e in evaluations_b.json["evaluations"]],
            [self.evaluation_b.id],
        )

        own_model = self.client_a.get(f"/api/ml/models/{self.model_a.id}")
        own_result = self.client_a.get(
            f"/api/ml/evaluations/{self.evaluation_a.id}"
        )
        self.assertEqual(own_model.status_code, 200)
        self.assertEqual(own_result.status_code, 200)
        self.assertEqual(own_result.json["evaluation"]["metrics"]["accuracy"], 0.9)
        self.assertNotIn("model_path", own_model.json["model"])
        self.assertNotIn("file_path", own_result.json["evaluation"])

    def test_nfr_5_st_1_and_sec_dat_1_lists_do_not_disclose_foreign_resources(self):
        """NFR-5-ST-1 / SEC-DAT-1-ST-1: Resource lists are owner-scoped."""
        for client, foreign_name, foreign_report in (
            (self.client_a, "owner-b.csv", "owner-b-report"),
            (self.client_b, "owner-a.csv", "owner-a-report"),
        ):
            payloads = [
                client.get("/api/dataset").get_data(as_text=True),
                client.get("/api/ml/models").get_data(as_text=True),
                client.get("/api/ml/evaluations").get_data(as_text=True),
            ]
            for payload in payloads:
                self.assertNotIn(foreign_name, payload)
                self.assertNotIn(foreign_report, payload)

    def test_mismatched_model_or_evaluation_ownership_is_never_visible(self):
        """SEC-AZ-2-ST-1: Related owner IDs must all agree for access."""
        model_list = self.client_a.get("/api/ml/models").json["models"]
        evaluation_list = self.client_a.get("/api/ml/evaluations").json["evaluations"]
        self.assertNotIn(
            self.mismatched_model.id, [item["id"] for item in model_list]
        )
        self.assertEqual(
            self.client_a.get(
                f"/api/ml/models/{self.mismatched_model.id}"
            ).status_code,
            404,
        )
        # The database integrity trigger rejects cross-owner evaluations before
        # they can become visible through any API endpoint.
        invalid_evaluation = EvaluationResult(
            user_id=self.user_a.id,
            model_id=self.model_b.id,
            metrics_json={"accuracy": 1.0},
        )
        db.session.add(invalid_evaluation)
        with self.assertRaises(IntegrityError):
            db.session.commit()
        db.session.rollback()
        self.assertEqual(
            self.client_a.get("/api/ml/evaluations").status_code, 200
        )

    def test_nfr_4_st_1_anonymous_direct_requests_are_rejected(self):
        """NFR-4-ST-1: Authorization is enforced by the backend, not the UI."""
        anonymous = self.app.test_client()
        paths = [
            ("GET", "/api/dataset"),
            ("GET", f"/api/dataset/{self.dataset_a.id}"),
            ("GET", "/api/ml/models"),
            ("GET", f"/api/ml/models/{self.model_a.id}"),
            ("GET", "/api/ml/evaluations"),
            ("GET", f"/api/ml/evaluations/{self.evaluation_a.id}"),
        ]
        for method, path in paths:
            with self.subTest(path=path):
                response = anonymous.open(path, method=method)
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.json["error"], "Authentication required")


if __name__ == "__main__":
    unittest.main()
