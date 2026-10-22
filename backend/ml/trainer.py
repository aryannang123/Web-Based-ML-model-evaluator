"""Task-aware scikit-learn model selection and artifact persistence."""

import os
import tempfile

import joblib
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
from sklearn.pipeline import Pipeline
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor

from ml.preprocessor import DataPreprocessor


class ModelTrainer:
    SUPPORTED_ALGORITHMS = {
        "classification": [
            "logistic_regression", "decision_tree", "random_forest", "knn"
        ],
        "regression": [
            "linear_regression", "decision_tree", "random_forest", "knn"
        ],
    }

    @classmethod
    def build_estimator(cls, algorithm_name, task_type, random_state=42,
                        training_rows=5):
        if task_type not in cls.SUPPORTED_ALGORITHMS:
            raise ValueError("Task type must be classification or regression.")
        if algorithm_name not in cls.SUPPORTED_ALGORITHMS[task_type]:
            raise ValueError("Algorithm is not supported for the selected task.")
        if algorithm_name == "logistic_regression":
            return LogisticRegression(max_iter=1000, random_state=random_state)
        if algorithm_name == "linear_regression":
            return LinearRegression()
        if algorithm_name == "decision_tree":
            estimator = (
                DecisionTreeClassifier if task_type == "classification"
                else DecisionTreeRegressor
            )
            return estimator(random_state=random_state)
        if algorithm_name == "random_forest":
            estimator = (
                RandomForestClassifier if task_type == "classification"
                else RandomForestRegressor
            )
            return estimator(n_estimators=100, random_state=random_state, n_jobs=1)
        if algorithm_name == "knn":
            neighbors = max(1, min(5, int(training_rows)))
            return (
                KNeighborsClassifier(n_neighbors=neighbors)
                if task_type == "classification"
                else KNeighborsRegressor(n_neighbors=neighbors)
            )
        raise ValueError("Unsupported algorithm.")

    @classmethod
    def train(cls, algorithm_name, task_type, X_train, y_train, **kwargs):
        estimator = cls.build_estimator(
            algorithm_name,
            task_type,
            random_state=kwargs.get("random_state", 42),
            training_rows=len(X_train),
        )
        pipeline = Pipeline([
            ("preprocessor", DataPreprocessor.make_transformer(
                X_train, kwargs.get("preprocessing")
            )),
            ("estimator", estimator),
        ])
        pipeline.fit(X_train, y_train)
        return pipeline

    @staticmethod
    def save(model, filepath):
        directory = os.path.dirname(filepath)
        os.makedirs(directory, exist_ok=True)
        descriptor, temporary_path = tempfile.mkstemp(
            prefix=".model-", suffix=".joblib", dir=directory
        )
        os.close(descriptor)
        try:
            joblib.dump(model, temporary_path)
            os.replace(temporary_path, filepath)
        finally:
            if os.path.exists(temporary_path):
                os.remove(temporary_path)

    @staticmethod
    def load(filepath):
        return joblib.load(filepath)
