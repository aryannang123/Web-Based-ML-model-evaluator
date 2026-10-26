# Machine Learning Model Training Module
#
# TODO: US-17: Implement ML algorithm selection (Assigned to: @gaganraghavan)
# TODO: US-18: Implement model training (Assigned to: @aryannang123)

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
