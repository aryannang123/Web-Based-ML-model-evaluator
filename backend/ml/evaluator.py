# Machine Learning Model Evaluation Module

import math

from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
)

class ModelEvaluator:
    """Computes evaluation metrics and generates comparison data."""

    @staticmethod
    def evaluate(model, X_test, y_test, task_type: str):
        """Calculate Accuracy, Precision, Recall, F1 or MSE, RMSE, R2 (US-19)."""
        predictions = model.predict(X_test)
        if task_type == "classification":
            metrics = {
                "accuracy": float(accuracy_score(y_test, predictions)),
                "precision_weighted": float(precision_score(
                    y_test, predictions, average="weighted", zero_division=0
                )),
                "recall_weighted": float(recall_score(
                    y_test, predictions, average="weighted", zero_division=0
                )),
                "f1_weighted": float(f1_score(
                    y_test, predictions, average="weighted", zero_division=0
                )),
            }
            report = classification_report(
                y_test, predictions, output_dict=True, zero_division=0
            )
            return metrics, ModelEvaluator.generate_confusion_matrix(y_test, predictions), report
        if task_type == "regression":
            mse = float(mean_squared_error(y_test, predictions))
            r2 = float(r2_score(y_test, predictions))
            return {
                "mse": mse,
                "rmse": math.sqrt(mse),
                "r2": r2 if math.isfinite(r2) else None,
            }, None, None
        raise ValueError("task_type must be classification or regression.")

    @staticmethod
    def generate_confusion_matrix(y_true, y_pred):
        """Generate confusion matrix array for classification tasks (US-19)."""
        return confusion_matrix(y_true, y_pred).tolist()
