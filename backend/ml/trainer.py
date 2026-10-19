from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
import joblib
import os

class ModelTrainer:
    """Instantiates and trains ML models matching the supported algorithms in the SRS."""

    SUPPORTED_ALGORITHMS = {
        "classification": {
            "logistic_regression": LogisticRegression,
            "decision_tree": DecisionTreeClassifier,
            "random_forest": RandomForestClassifier,
            "knn": KNeighborsClassifier
        },
        "regression": {
            "linear_regression": LinearRegression,
            "decision_tree": DecisionTreeRegressor,
            "random_forest": RandomForestRegressor,
            "knn": KNeighborsRegressor
        }
    }

    @classmethod
    def get_supported_algorithms(cls):
        return {
            task: list(models.keys()) for task, models in cls.SUPPORTED_ALGORITHMS.items()
        }

    @classmethod
    def train(cls, algorithm_name: str, task_type: str, X_train, y_train, hyperparameters: dict = None):
        """Train a model given algorithm and task type."""
        task_models = cls.SUPPORTED_ALGORITHMS.get(task_type.lower())
        if not task_models or algorithm_name.lower() not in task_models:
            raise ValueError(f"Algorithm '{algorithm_name}' not supported for {task_type}.")

        model_cls = task_models[algorithm_name.lower()]
        params = hyperparameters or {}

        # Default random_state where supported
        if "random_state" not in params and "random_state" in model_cls.__init__.__code__.co_varnames:
            params["random_state"] = 42

        model = model_cls(**params)
        model.fit(X_train, y_train)
        return model

    @staticmethod
    def save_model(model, filepath: str):
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        joblib.dump(model, filepath)
        return filepath

    @staticmethod
    def load_model(filepath: str):
        return joblib.load(filepath)
