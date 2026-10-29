# Machine Learning Model Training Module

import joblib
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor


class ModelTrainer:
    """Trains classification and regression models using scikit-learn."""

    SUPPORTED_ALGORITHMS = [
        "logistic_regression",
        "linear_regression",
        "decision_tree",
        "random_forest",
        "knn"
    ]

    ALGORITHM_CATALOG = {
        "classification": [
            {"id": "logistic_regression", "label": "Logistic Regression", "description": "Linear classifier for categorical targets."},
            {"id": "decision_tree", "label": "Decision Tree", "description": "Interpretable tree-based classifier."},
            {"id": "random_forest", "label": "Random Forest", "description": "Ensemble of randomized decision trees."},
            {"id": "knn", "label": "K-Nearest Neighbors", "description": "Classifies using nearby training samples."},
        ],
        "regression": [
            {"id": "linear_regression", "label": "Linear Regression", "description": "Linear model for numeric targets."},
            {"id": "decision_tree", "label": "Decision Tree Regressor", "description": "Tree-based regressor for numeric targets."},
            {"id": "random_forest", "label": "Random Forest Regressor", "description": "Ensemble regressor using randomized trees."},
            {"id": "knn", "label": "K-Nearest Neighbors Regressor", "description": "Predicts from nearby training samples."},
        ],
    }

    @classmethod
    def algorithms_for(cls, task_type=None):
        """Return a copy of the supported algorithm catalog."""
        if task_type is None:
            return {task: [dict(item) for item in entries] for task, entries in cls.ALGORITHM_CATALOG.items()}
        if task_type not in cls.ALGORITHM_CATALOG:
            raise ValueError("task_type must be classification or regression.")
        return [dict(item) for item in cls.ALGORITHM_CATALOG[task_type]]

    @classmethod
    def train(cls, algorithm_name: str, task_type: str, X_train, y_train, **kwargs):
        """Fit a supported estimator with preprocessing learned from training data."""
        estimator = cls.create_estimator(algorithm_name, task_type)
        from ml.preprocessor import DataPreprocessor

        scale_numeric = algorithm_name in {
            "logistic_regression", "linear_regression", "knn"
        }
        pipeline = DataPreprocessor.build_pipeline(
            X_train, estimator, scale_numeric=scale_numeric
        )
        pipeline.fit(X_train, y_train)
        return pipeline

    @staticmethod
    def create_estimator(algorithm_name, task_type):
        if task_type == "classification":
            estimators = {
                "logistic_regression": LogisticRegression(max_iter=1000, random_state=42),
                "decision_tree": DecisionTreeClassifier(random_state=42),
                "random_forest": RandomForestClassifier(n_estimators=100, random_state=42),
                "knn": KNeighborsClassifier(n_neighbors=5),
            }
        elif task_type == "regression":
            estimators = {
                "linear_regression": LinearRegression(),
                "decision_tree": DecisionTreeRegressor(random_state=42),
                "random_forest": RandomForestRegressor(n_estimators=100, random_state=42),
                "knn": KNeighborsRegressor(n_neighbors=5),
            }
        else:
            raise ValueError("task_type must be classification or regression.")

        estimator = estimators.get(algorithm_name)
        if estimator is None:
            raise ValueError("The selected algorithm is not supported for this task type.")
        return estimator

    @staticmethod
    def save(model, filepath: str):
        """Serialize model weights with joblib."""
        joblib.dump(model, filepath)
