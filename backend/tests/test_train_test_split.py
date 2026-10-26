import io
import os
import tempfile
import unittest
from uuid import uuid4

from app import create_app
from database.db import db
from ml.preprocessor import DataPreprocessor
from models.dataset import Dataset
from models.evaluation import EvaluationResult
from models.model import MLModel
from models.user import User


class TestTrainTestSplit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory(prefix="ml-evaluator-split-tests-")

        class TestConfig:
            TESTING = True
            SECRET_KEY = "split-test-key"
            SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
            SQLALCHEMY_TRACK_MODIFICATIONS = False
            UPLOAD_FOLDER = os.path.join(cls.temp_dir.name, "uploads")
            SAVED_MODELS_FOLDER = os.path.join(cls.temp_dir.name, "models")
            MIN_DATA_ROWS = 2
            MIN_DATA_COLUMNS = 2

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
        suffix = uuid4().hex
        self.username = f"split_{suffix[:12]}"
        self.client.post("/api/auth/register", json={
            "username": self.username,
            "email": f"{suffix}@example.com",
            "password": "StrongPass123!",
        })
        login = self.client.post("/api/auth/login", json={
            "username": self.username,
            "password": "StrongPass123!",
        })
        self.assertEqual(login.status_code, 200)
        self.user = User.query.filter_by(username=self.username).one()

    def tearDown(self):
        db.session.rollback()
        EvaluationResult.query.delete()
        MLModel.query.delete()
        Dataset.query.delete()
        User.query.delete()
        db.session.commit()
        for folder in (self.app.config["UPLOAD_FOLDER"], self.app.config["SAVED_MODELS_FOLDER"]):
            if os.path.isdir(folder):
                for name in os.listdir(folder):
                    os.remove(os.path.join(folder, name))

    @staticmethod
    def csv_rows(count):
        rows = ["feature,target"]
        rows.extend(f"{index},{'yes' if index % 2 else 'no'}" for index in range(count))
        return ("\n".join(rows) + "\n").encode("utf-8")

    def upload(self, count=20):
        response = self.client.post(
            "/api/dataset/upload",
            data={"file": (io.BytesIO(self.csv_rows(count)), "data.csv")},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 201, response.get_data(as_text=True))
        return response.json["dataset_id"]

    def evaluate(self, dataset_id, endpoint="evaluate", **overrides):
        payload = {
            "dataset_id": dataset_id,
            "target_column": "target",
            "algorithm": "decision_tree",
            "task_type": "classification",
        }
        payload.update(overrides)
        return self.client.post(f"/api/ml/{endpoint}", json=payload)

    def test_split_helper_defaults_to_80_20_and_is_deterministic(self):
        X = list(range(10))
        y = list(range(10))
        first = DataPreprocessor.split(X, y)
        second = DataPreprocessor.split(X, y)
        self.assertEqual((len(first[0]), len(first[1])), (8, 2))
        self.assertEqual(first, second)

    def test_split_helper_uses_custom_70_30_ratio(self):
        train_x, test_x, train_y, test_y = DataPreprocessor.split(
            list(range(20)), list(range(20)), test_size=0.3
        )
        self.assertEqual((len(train_x), len(test_x)), (14, 6))
        self.assertEqual((len(train_y), len(test_y)), (14, 6))

    def test_split_helper_rejects_invalid_ratio_types_and_boundaries(self):
        for value in ("0.2", True, 0, 1, -0.1, 1.1, float("inf"), float("nan")):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "test_size"):
                    DataPreprocessor.split([1, 2], [1, 2], test_size=value)

    def test_endpoint_defaults_to_real_80_20_partitions(self):
        dataset_id = self.upload()

        response = self.evaluate(dataset_id)

        self.assertEqual(response.status_code, 201, response.get_data(as_text=True))
        self.assertEqual(response.json["split"]["requested_test_size"], 0.2)
        self.assertEqual(response.json["split"]["train_rows"], 16)
        self.assertEqual(response.json["split"]["test_rows"], 4)
        model = db.session.get(MLModel, response.json["model_id"])
        self.assertEqual(model.config_json["test_size"], 0.2)
        self.assertIsNotNone(db.session.get(EvaluationResult, response.json["evaluation_id"]))

    def test_endpoint_uses_custom_70_30_partition_sizes(self):
        dataset_id = self.upload()

        response = self.evaluate(dataset_id, test_size=0.3)

        self.assertEqual(response.status_code, 201, response.get_data(as_text=True))
        self.assertEqual(response.json["split"]["requested_test_size"], 0.3)
        self.assertEqual(response.json["split"]["train_rows"], 14)
        self.assertEqual(response.json["split"]["test_rows"], 6)

    def test_train_endpoint_uses_the_same_selected_split(self):
        dataset_id = self.upload()

        response = self.evaluate(dataset_id, endpoint="train", test_size=0.3)

        self.assertEqual(response.status_code, 201, response.get_data(as_text=True))
        self.assertEqual(response.json["split"]["train_rows"], 14)
        self.assertEqual(response.json["split"]["test_rows"], 6)

    def test_endpoint_rejects_invalid_ratio_values(self):
        dataset_id = self.upload()
        for value in ("30%", True, 0, 1, -0.1, 1.1, float("inf"), float("nan")):
            with self.subTest(value=value):
                response = self.evaluate(dataset_id, test_size=value)
                self.assertEqual(response.status_code, 400)
                self.assertIn("test_size", response.json["error"])

    def test_endpoint_rejects_splits_without_both_partitions(self):
        dataset_id = self.upload(count=5)

        response = self.evaluate(dataset_id, test_size=0.99)

        self.assertEqual(response.status_code, 400)
        self.assertIn("training or testing", response.json["error"].lower())

    def test_endpoint_enforces_algorithm_sample_minimum(self):
        dataset_id = self.upload(count=7)

        response = self.evaluate(dataset_id, algorithm="knn", test_size=0.3)

        self.assertEqual(response.status_code, 400)
        self.assertIn("requires at least 5", response.json["error"])

    def test_evaluate_endpoint_requires_authentication(self):
        unauthenticated = self.app.test_client()
        response = unauthenticated.post("/api/ml/evaluate", json={"dataset_id": 1})
        self.assertEqual(response.status_code, 401)

    def test_evaluate_endpoint_denies_another_users_dataset(self):
        dataset_id = self.upload()
        other_client = self.app.test_client()
        token = uuid4().hex
        other_client.post("/api/auth/register", json={
            "username": f"other_{token[:12]}",
            "email": f"{token}@example.com",
            "password": "StrongPass123!",
        })
        other_client.post("/api/auth/login", json={
            "username": f"other_{token[:12]}",
            "password": "StrongPass123!",
        })

        response = other_client.post("/api/ml/evaluate", json={
            "dataset_id": dataset_id,
            "target_column": "target",
            "algorithm": "decision_tree",
            "task_type": "classification",
            "test_size": 0.3,
        })

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json["error"], "Dataset not found")


if __name__ == "__main__":
    unittest.main()
