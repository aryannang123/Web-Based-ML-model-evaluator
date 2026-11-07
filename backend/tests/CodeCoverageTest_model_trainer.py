"""Line-coverage cases for the web evaluator's core model-training module.

Run from backend with:
    python -m coverage run --source=ml.trainer -m pytest -q tests/CodeCoverageTest_model_trainer.py
"""

import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ml.trainer import ModelTrainer


def test_algorithm_catalog_supports_both_tasks_and_returns_copies():
    all_algorithms = ModelTrainer.algorithms_for()
    assert set(all_algorithms) == {"classification", "regression"}
    assert len(all_algorithms["classification"]) == 4
    assert len(all_algorithms["regression"]) == 4

    # The returned catalog must not let a caller mutate the class-level data.
    all_algorithms["classification"][0]["label"] = "changed by caller"
    assert ModelTrainer.algorithms_for("classification")[0]["label"] != "changed by caller"
    assert ModelTrainer.algorithms_for("regression")[0]["id"] == "linear_regression"


def test_numpy_features_train_classification_pipeline():
    features = np.array([[0.0], [1.0], [2.0], [3.0], [4.0], [5.0]])
    labels = np.array([0, 0, 0, 1, 1, 1])
    model = ModelTrainer.train("decision_tree", "classification", features, labels)
    assert set(model.predict(pd.DataFrame({"col_0": [0.5, 4.5]}))).issubset({0, 1})


def test_dataframe_features_train_regression_pipeline():
    features = pd.DataFrame({"distance": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]})
    target = pd.Series([2.0, 4.0, 6.0, 8.0, 10.0, 12.0])
    model = ModelTrainer.train("linear_regression", "regression", features, target)
    assert model.predict(pd.DataFrame({"distance": [7.0]})).shape == (1,)


def test_validation_errors_cover_unsupported_and_incompatible_options():
    with pytest.raises(ValueError, match="task_type must be"):
        ModelTrainer.algorithms_for("clustering")
    with pytest.raises(ValueError, match="Unsupported algorithm"):
        ModelTrainer.train("not-an-algorithm", "classification", [[1], [2]], [0, 1])
    with pytest.raises(ValueError, match="Unsupported algorithm"):
        ModelTrainer.create_estimator("not-an-algorithm", "classification")
    with pytest.raises(ValueError, match="Unsupported task_type"):
        ModelTrainer.create_estimator("decision_tree", "clustering")
    with pytest.raises(ValueError, match="Unsupported task_type"):
        ModelTrainer.train("decision_tree", "clustering", [[1], [2]], [0, 1])
    with pytest.raises(ValueError, match="not compatible"):
        ModelTrainer.create_estimator("linear_regression", "classification")


def test_save_serializes_a_fitted_pipeline_and_creates_parent_directories():
    model = ModelTrainer.train(
        "decision_tree",
        "classification",
        np.array([[0], [1], [2], [3]]),
        np.array([0, 0, 1, 1]),
    )
    with tempfile.TemporaryDirectory(prefix="coverage-line-") as temp_dir:
        output = Path(temp_dir) / "nested" / "model.joblib"
        ModelTrainer.save(model, str(output))
        assert output.is_file()
