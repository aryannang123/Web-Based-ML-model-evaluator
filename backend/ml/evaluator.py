"""Metric calculation and comparison helpers."""

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
)


class ModelEvaluator:
    @staticmethod
    def evaluate(model, X_test, y_test, task_type):
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
            return {
                "task_type": task_type,
                "metrics": metrics,
                "confusion_matrix": ModelEvaluator.generate_confusion_matrix(
                    y_test, predictions
                ),
                "classes": [str(value) for value in np.unique(
                    np.concatenate([np.asarray(y_test), np.asarray(predictions)])
                )],
                "visualization": {
                    "kind": "classification_metrics",
                    "labels": list(metrics.keys()),
                    "values": list(metrics.values()),
                },
            }
        if task_type == "regression":
            mse = float(mean_squared_error(y_test, predictions))
            return {
                "task_type": task_type,
                "metrics": {
                    "mae": float(mean_absolute_error(y_test, predictions)),
                    "mse": mse,
                    "rmse": float(np.sqrt(mse)),
                    "r2": float(r2_score(y_test, predictions)),
                },
                "confusion_matrix": None,
                "classes": None,
                "visualization": {
                    "kind": "regression_residuals",
                    "points": [
                        {
                            "actual": float(actual),
                            "predicted": float(predicted),
                            "residual": float(actual - predicted),
                        }
                        for actual, predicted in list(zip(y_test, predictions))[:200]
                    ],
                },
            }
        raise ValueError("Task type must be classification or regression.")

    @staticmethod
    def generate_confusion_matrix(y_true, y_pred):
        labels = np.unique(np.concatenate([np.asarray(y_true), np.asarray(y_pred)]))
        return confusion_matrix(y_true, y_pred, labels=labels).tolist()
