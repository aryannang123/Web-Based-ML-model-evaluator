"""Decision-branch coverage cases for the ModelTrainer module.

Run from backend with:
    python -m coverage run --branch --source=ml.trainer -m pytest -q tests/BranchCoverageTest_model_trainer.py
"""

import numpy as np
import pandas as pd
import pytest
import tempfile
from pathlib import Path

from ml.trainer import ModelTrainer


def test_catalog_none_classification_regression_and_invalid_task_branches():
    assert set(ModelTrainer.algorithms_for()) == {"classification", "regression"}
    assert ModelTrainer.algorithms_for("classification")[0]["id"] == "logistic_regression"
    assert ModelTrainer.algorithms_for("regression")[0]["id"] == "linear_regression"
    with pytest.raises(ValueError, match="classification or regression"):
        ModelTrainer.algorithms_for("clustering")


def test_estimator_validation_branches_for_name_task_and_pairing():
    with pytest.raises(ValueError, match="Unsupported algorithm"):
        ModelTrainer.create_estimator("svm", "classification")
    with pytest.raises(ValueError, match="Unsupported task_type"):
        ModelTrainer.create_estimator("random_forest", "forecasting")
    with pytest.raises(ValueError, match="not compatible"):
        ModelTrainer.create_estimator("logistic_regression", "regression")
    with pytest.raises(ValueError, match="Unsupported algorithm"):
        ModelTrainer.train("svm", "classification", [[0], [1]], [0, 1])
    with pytest.raises(ValueError, match="Unsupported task_type"):
        ModelTrainer.train("decision_tree", "clustering", [[0], [1]], [0, 1])


def test_train_numpy_inputs_exercise_numeric_scaling_branch():
    x = np.array([[0.0], [1.0], [2.0], [3.0], [4.0], [5.0]])
    y = np.array([0, 0, 0, 1, 1, 1])
    fitted = ModelTrainer.train("knn", "classification", x, y)
    assert fitted.predict(pd.DataFrame({"col_0": [4.5]})).shape == (1,)


def test_train_dataframe_inputs_exercise_unscaled_estimator_branch():
    x = pd.DataFrame({"x": [0.0, 1.0, 2.0, 3.0, 4.0, 5.0]})
    y = pd.Series([0.0, 2.0, 4.0, 6.0, 8.0, 10.0])
    fitted = ModelTrainer.train("decision_tree", "regression", x, y)
    assert fitted.predict(pd.DataFrame({"x": [6.0]})).shape == (1,)


def test_save_branch_writes_fitted_model_to_nested_path():
    fitted = ModelTrainer.train(
        "decision_tree",
        "classification",
        np.array([[0], [1], [2], [3]]),
        np.array([0, 0, 1, 1]),
    )
    with tempfile.TemporaryDirectory(prefix="coverage-branch-") as temp_dir:
        output = Path(temp_dir) / "nested" / "model.joblib"
        ModelTrainer.save(fitted, str(output))
        assert output.is_file()
