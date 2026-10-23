import unittest
from uuid import uuid4

from app import create_app
from database.db import db
from models.dataset import Dataset
from models.evaluation import EvaluationResult
from models.model import MLModel
from models.user import User
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError


class TestEvaluationOwnership(unittest.TestCase):
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
        cls.context = cls.app.app_context()
        cls.context.push()

    @classmethod
    def tearDownClass(cls):
        db.session.remove()
        db.drop_all()
        cls.context.pop()

    def setUp(self):
        db.session.remove()
        self.owner = self.make_user()
        self.other_owner = self.make_user()
        db.session.add_all([self.owner, self.other_owner])
        db.session.flush()

        self.owner_model = self.make_model(self.owner)
        self.other_model = self.make_model(self.other_owner)
        db.session.add_all([self.owner_model, self.other_model])
        db.session.commit()

    def tearDown(self):
        db.session.rollback()
        EvaluationResult.query.delete()
        MLModel.query.delete()
        Dataset.query.delete()
        User.query.delete()
        db.session.commit()

    @staticmethod
    def make_user():
        token = uuid4().hex
        return User(
            username=f"user_{token[:12]}",
            email=f"{token}@example.com",
            password_hash="test-hash",
        )

    @staticmethod
    def make_model(user):
        dataset = Dataset(
            user=user,
            filename="data.csv",
            file_path="/tmp/data.csv",
            file_size=10,
            row_count=1,
            column_count=1,
        )
        return MLModel(
            user=user,
            dataset=dataset,
            model_name="test-model",
            algorithm="test",
            status="complete",
        )

    def test_same_owner_evaluation_is_accepted(self):
        evaluation = EvaluationResult(
            user_id=self.owner.id,
            model_id=self.owner_model.id,
            metrics_json={"accuracy": 1.0},
        )
        db.session.add(evaluation)
        db.session.commit()

        self.assertIsNotNone(evaluation.id)

    def test_evaluation_for_another_users_model_is_rejected(self):
        evaluation = EvaluationResult(
            user_id=self.owner.id,
            model_id=self.other_model.id,
            metrics_json={"accuracy": 1.0},
        )
        db.session.add(evaluation)

        with self.assertRaises(IntegrityError):
            db.session.commit()
        db.session.rollback()

        self.assertEqual(EvaluationResult.query.count(), 0)

    def test_existing_tables_receive_ownership_triggers_on_initialization(self):
        trigger_names = (
            "evaluation_owner_matches_model_owner_insert",
            "evaluation_owner_matches_model_owner_update",
            "evaluation_owner_matches_model_owner_model_update",
        )
        for trigger_name in trigger_names:
            db.session.execute(text(f"DROP TRIGGER {trigger_name}"))
        db.session.commit()

        # create_all still emits metadata after_create when the tables exist.
        db.create_all()

        evaluation = EvaluationResult(
            user_id=self.owner.id,
            model_id=self.other_model.id,
            metrics_json={"accuracy": 1.0},
        )
        db.session.add(evaluation)
        with self.assertRaises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def test_updating_evaluation_to_another_users_model_is_rejected(self):
        evaluation = EvaluationResult(
            user_id=self.owner.id,
            model_id=self.owner_model.id,
            metrics_json={"accuracy": 1.0},
        )
        db.session.add(evaluation)
        db.session.commit()

        evaluation.model_id = self.other_model.id
        with self.assertRaises(IntegrityError):
            db.session.commit()
        db.session.rollback()

        persisted = db.session.get(EvaluationResult, evaluation.id)
        self.assertEqual(persisted.model_id, self.owner_model.id)
        self.assertEqual(persisted.user_id, self.owner.id)

    def test_model_owner_cannot_change_away_from_existing_evaluations(self):
        evaluation = EvaluationResult(
            user_id=self.owner.id,
            model_id=self.owner_model.id,
            metrics_json={"accuracy": 1.0},
        )
        db.session.add(evaluation)
        db.session.commit()

        self.owner_model.user_id = self.other_owner.id
        with self.assertRaises(IntegrityError):
            db.session.commit()
        db.session.rollback()

        persisted = db.session.get(MLModel, self.owner_model.id)
        self.assertEqual(persisted.user_id, self.owner.id)


if __name__ == "__main__":
    unittest.main()
