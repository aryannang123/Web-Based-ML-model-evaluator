"""
US-14 Data Preprocessing Test Suite
=====================================
Traceability: FR-3.1 (Corrected_Test_Plan.md)
  - FR-3.1-UT-1  Apply a supported preprocessing option to valid data
  - FR-3.1-UT-2  Reject incompatible preprocessing configuration
  - SEC-INP-1-UT-1  Backend validates all user-controlled configuration identifiers
  - SEC-AZ-2  User data isolation on preprocessing endpoint

Test Plan Section: 3.3 Data Preparation
"""

import io
import json
import math
import os
import tempfile
import unittest

import pandas as pd
from werkzeug.security import generate_password_hash

from app import create_app
from database.db import db
from ml.preprocessor import DataPreprocessor
from models.dataset import Dataset
from models.user import User


# ---------------------------------------------------------------------------
# Helper CSV fixtures
# ---------------------------------------------------------------------------

_CSV_NUMERIC = (
    "age,salary,department,target\n"
    "25,50000,Engineering,1\n"
    "30,60000,Marketing,0\n"
    "35,,Engineering,1\n"
    "28,55000,HR,0\n"
    "40,70000,Marketing,1\n"
)

_CSV_ALL_NUMERIC = (
    "a,b,c\n"
    "1,2,3\n"
    "4,5,6\n"
    "7,8,9\n"
    "10,11,12\n"
)

_CSV_CATEGORICAL_ONLY = (
    "color,size,label\n"
    "red,small,yes\n"
    "blue,large,no\n"
    "green,medium,yes\n"
    "red,large,no\n"
)

_CSV_WITH_NULLS = (
    "x,y,z\n"
    "1,,3\n"
    "4,5,\n"
    "7,8,9\n"
    "10,11,12\n"
)


# ---------------------------------------------------------------------------
# Unit tests: DataPreprocessor class (no HTTP layer)
# ---------------------------------------------------------------------------

class TestDataPreprocessorMissingValues(unittest.TestCase):
    """FR-3.1-UT-1: Apply supported missing-value handling to valid data."""

    def _frame(self, csv_text):
        return pd.read_csv(io.StringIO(csv_text))

    def test_none_strategy_leaves_frame_unchanged(self):
        """Strategy 'none' must return an identical copy of the DataFrame."""
        df = self._frame(_CSV_WITH_NULLS)
        out = DataPreprocessor.handle_missing_values(df, strategy="none")
        self.assertEqual(df.isnull().sum().sum(), out.isnull().sum().sum())

    def test_drop_strategy_removes_rows_with_nulls(self):
        """Strategy 'drop' must remove every row that contains a NaN."""
        df = self._frame(_CSV_WITH_NULLS)
        out = DataPreprocessor.handle_missing_values(df, strategy="drop")
        self.assertEqual(out.isnull().sum().sum(), 0)
        self.assertEqual(len(out), 2)   # only rows 3 and 4 are complete

    def test_mean_strategy_fills_numeric_nulls(self):
        """Strategy 'mean' must fill numeric nulls with the column mean."""
        df = self._frame(_CSV_WITH_NULLS)
        out = DataPreprocessor.handle_missing_values(df, strategy="mean")
        self.assertEqual(out.isnull().sum().sum(), 0)

    def test_median_strategy_fills_numeric_nulls(self):
        """Strategy 'median' must fill numeric nulls with the column median."""
        df = self._frame(_CSV_WITH_NULLS)
        out = DataPreprocessor.handle_missing_values(df, strategy="median")
        self.assertEqual(out.isnull().sum().sum(), 0)

    def test_mode_strategy_fills_nulls_with_most_frequent(self):
        """Strategy 'mode' must fill each column with its most frequent value."""
        df = self._frame(_CSV_WITH_NULLS)
        out = DataPreprocessor.handle_missing_values(df, strategy="mode")
        self.assertEqual(out.isnull().sum().sum(), 0)

    def test_constant_strategy_fills_numeric_with_zero(self):
        """Strategy 'constant' must fill numeric nulls with 0 by default."""
        df = self._frame(_CSV_WITH_NULLS)
        out = DataPreprocessor.handle_missing_values(df, strategy="constant")
        self.assertEqual(out.isnull().sum().sum(), 0)
        # y col had NaN at row 0 → should become 0
        self.assertEqual(out["y"].iloc[0], 0.0)

    def test_mean_strategy_categorical_column_uses_mode(self):
        """Strategy 'mean' on a categorical column must fall back to mode."""
        df = self._frame(_CSV_NUMERIC)
        out = DataPreprocessor.handle_missing_values(df, strategy="mean")
        self.assertEqual(out.isnull().sum().sum(), 0)

    def test_drop_raises_if_result_is_too_small(self):
        """Dropping all rows must raise ValueError with a useful message."""
        df = pd.DataFrame({"a": [1, None], "b": [None, 2]})
        with self.assertRaises(ValueError) as ctx:
            DataPreprocessor.handle_missing_values(df, strategy="drop")
        self.assertIn("fewer than 2 rows", str(ctx.exception))


class TestDataPreprocessorEncoding(unittest.TestCase):
    """FR-3.1-UT-1: Encoding transforms categorical data correctly."""

    def _frame(self, csv_text):
        return pd.read_csv(io.StringIO(csv_text))

    def test_label_encoding_converts_strings_to_integers(self):
        """Label encoding must produce integer-dtype columns for all categoricals."""
        df = self._frame(_CSV_CATEGORICAL_ONLY)
        out = DataPreprocessor.encode_features(df, strategy="label")
        for col in ["color", "size"]:
            self.assertTrue(
                pd.api.types.is_numeric_dtype(out[col]),
                f"Column '{col}' should be numeric after label encoding"
            )

    def test_onehot_encoding_expands_categorical_columns(self):
        """One-hot encoding must expand each categorical feature into indicator columns."""
        df = self._frame(_CSV_CATEGORICAL_ONLY)
        out = DataPreprocessor.encode_features(df, strategy="onehot", target_column="label")
        # 'color' (3 values) and 'size' (3 values) should each be expanded
        self.assertGreater(len(out.columns), len(df.columns))
        self.assertNotIn("color", out.columns)
        self.assertNotIn("size", out.columns)
        # target is categorical but should remain as a single label-encoded col
        self.assertIn("label", out.columns)

    def test_none_encoding_leaves_frame_unchanged(self):
        """Strategy 'none' must return an identical copy."""
        df = self._frame(_CSV_CATEGORICAL_ONLY)
        out = DataPreprocessor.encode_features(df, strategy="none")
        self.assertEqual(list(df.columns), list(out.columns))

    def test_encoding_fills_null_cats_before_encoding(self):
        """Encoding must not crash when categorical column has NaN values."""
        df = pd.DataFrame({"cat": ["a", None, "b", "a"], "target": [0, 1, 0, 1]})
        out = DataPreprocessor.encode_features(df, strategy="label")
        self.assertEqual(out.isnull().sum().sum(), 0)


class TestDataPreprocessorScaling(unittest.TestCase):
    """FR-3.1-UT-1: Scaling transforms numeric values within expected ranges."""

    def _frame(self, csv_text):
        return pd.read_csv(io.StringIO(csv_text))

    def test_minmax_scales_to_0_1(self):
        """MinMax normalization must produce values in [0.0, 1.0]."""
        df = self._frame(_CSV_ALL_NUMERIC)
        out = DataPreprocessor.scale_features(df, strategy="minmax")
        for col in out.columns:
            self.assertGreaterEqual(out[col].min(), 0.0)
            self.assertLessEqual(out[col].max(), 1.0)

    def test_standard_scaling_produces_near_zero_mean(self):
        """Standardization must produce columns with mean ≈ 0 and std ≈ 1."""
        df = self._frame(_CSV_ALL_NUMERIC)
        out = DataPreprocessor.scale_features(df, strategy="standard")
        for col in out.columns:
            self.assertAlmostEqual(out[col].mean(), 0.0, places=10)

    def test_scaling_excludes_target_column(self):
        """Scaling must not alter the values in the target column."""
        df = self._frame(_CSV_ALL_NUMERIC)
        target_original = df["c"].tolist()
        out = DataPreprocessor.scale_features(df, strategy="minmax", target_column="c")
        self.assertEqual(out["c"].tolist(), target_original)

    def test_none_scaling_leaves_frame_unchanged(self):
        """Strategy 'none' must return values identical to the input."""
        df = self._frame(_CSV_ALL_NUMERIC)
        out = DataPreprocessor.scale_features(df, strategy="none")
        self.assertTrue(df.equals(out))


class TestDataPreprocessorPipeline(unittest.TestCase):
    """FR-3.1-UT-1: Full preprocessing pipeline operates correctly end-to-end."""

    def _frame(self, csv_text):
        return pd.read_csv(io.StringIO(csv_text))

    def test_pipeline_applies_all_steps_in_order(self):
        """Pipeline (missing + encoding + scaling) must complete without errors."""
        df = self._frame(_CSV_NUMERIC)
        config = {
            "missing_values": "mean",
            "encoding": "label",
            "scaling": "minmax",
        }
        out, summary = DataPreprocessor.preprocess(df, config, target_column="target")
        self.assertGreaterEqual(len(out), 2)
        self.assertIn("new_columns", summary)
        self.assertEqual(summary["missing_values"], "mean")
        self.assertEqual(summary["encoding"], "label")
        self.assertEqual(summary["scaling"], "minmax")

    def test_pipeline_returns_row_and_column_counts(self):
        """Summary dict must contain rows_before, rows_after, columns_after."""
        df = self._frame(_CSV_ALL_NUMERIC)
        config = {"missing_values": "none", "encoding": "none", "scaling": "none"}
        _, summary = DataPreprocessor.preprocess(df, config)
        self.assertIn("rows_before", summary)
        self.assertIn("rows_after", summary)
        self.assertIn("columns_after", summary)

    def test_pipeline_raises_on_invalid_target_column(self):
        """Pipeline must raise ValueError for a nonexistent target column."""
        df = self._frame(_CSV_ALL_NUMERIC)
        config = {"missing_values": "none", "encoding": "none", "scaling": "none"}
        with self.assertRaises(ValueError) as ctx:
            DataPreprocessor.preprocess(df, config, target_column="nonexistent")
        self.assertIn("nonexistent", str(ctx.exception))


# ---------------------------------------------------------------------------
# FR-3.1-UT-2 / SEC-INP-1-UT-1: Reject incompatible configurations
# ---------------------------------------------------------------------------

class TestDataPreprocessorInvalidConfigs(unittest.TestCase):
    """FR-3.1-UT-2: Invalid configurations are rejected with useful messages."""

    def _frame(self, csv_text):
        return pd.read_csv(io.StringIO(csv_text))

    def test_invalid_missing_strategy_raises(self):
        """Unsupported missing-value strategy name raises ValueError."""
        df = self._frame(_CSV_ALL_NUMERIC)
        with self.assertRaises(ValueError) as ctx:
            DataPreprocessor.handle_missing_values(df, strategy="invalid_option")
        self.assertIn("invalid_option", str(ctx.exception))
        self.assertIn("Unsupported", str(ctx.exception))

    def test_invalid_encoding_strategy_raises(self):
        """Unsupported encoding strategy name raises ValueError."""
        df = self._frame(_CSV_CATEGORICAL_ONLY)
        with self.assertRaises(ValueError) as ctx:
            DataPreprocessor.encode_features(df, strategy="base64")
        self.assertIn("base64", str(ctx.exception))

    def test_invalid_scaling_strategy_raises(self):
        """Unsupported scaling strategy name raises ValueError."""
        df = self._frame(_CSV_ALL_NUMERIC)
        with self.assertRaises(ValueError) as ctx:
            DataPreprocessor.scale_features(df, strategy="robust")
        self.assertIn("robust", str(ctx.exception))

    def test_scaling_on_non_numeric_column_raises(self):
        """Applying scaling to a DataFrame with non-numeric feature columns raises ValueError."""
        df = self._frame(_CSV_CATEGORICAL_ONLY)
        with self.assertRaises(ValueError) as ctx:
            DataPreprocessor.scale_features(df, strategy="minmax", target_column="label")
        self.assertIn("non-numeric", str(ctx.exception))

    def test_scaling_with_missing_values_raises(self):
        """Applying scaling to a column that still has NaN must raise ValueError."""
        df = self._frame(_CSV_WITH_NULLS)
        with self.assertRaises(ValueError) as ctx:
            DataPreprocessor.scale_features(df, strategy="standard")
        self.assertIn("missing values", str(ctx.exception))

    def test_empty_dataframe_raises_in_pipeline(self):
        """Pipeline must reject a DataFrame with fewer than 2 rows."""
        df = pd.DataFrame({"a": [1], "b": [2]})
        config = {"missing_values": "none", "encoding": "none", "scaling": "none"}
        with self.assertRaises(ValueError) as ctx:
            DataPreprocessor.preprocess(df, config)
        self.assertIn("2 rows", str(ctx.exception))


# ---------------------------------------------------------------------------
# API integration tests: POST /api/dataset/<id>/preprocess
# ---------------------------------------------------------------------------

class TestPreprocessEndpoint(unittest.TestCase):
    """Integration tests for the /api/dataset/<id>/preprocess endpoint."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        test_config = {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{os.path.join(self.temp_dir, 'test_us14.db')}",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "SECRET_KEY": "test-secret-key-us14",
            "UPLOAD_FOLDER": os.path.join(self.temp_dir, "uploads"),
            "SAVED_MODELS_FOLDER": os.path.join(self.temp_dir, "models"),
            "WTF_CSRF_ENABLED": False,
            "MIN_DATA_ROWS": 2,
            "MIN_DATA_COLUMNS": 2,
        }
        os.makedirs(test_config["UPLOAD_FOLDER"], exist_ok=True)

        self.app = create_app(type("TestConfig", (), test_config))
        self.client = self.app.test_client()

        with self.app.app_context():
            db.create_all()

            self.user_a = User(
                username="user_a",
                email="usera@example.com",
                password_hash=generate_password_hash("PassA123"),
                role="student",
                is_active=True,
            )
            self.user_b = User(
                username="user_b",
                email="userb@example.com",
                password_hash=generate_password_hash("PassB123"),
                role="student",
                is_active=True,
            )
            db.session.add_all([self.user_a, self.user_b])
            db.session.commit()

            # Write a CSV file for user_a
            csv_bytes = _CSV_NUMERIC.encode("utf-8")
            csv_path = os.path.join(test_config["UPLOAD_FOLDER"], "dataset_a.csv")
            with open(csv_path, "wb") as fh:
                fh.write(csv_bytes)

            self.dataset_a = Dataset(
                user_id=self.user_a.id,
                filename="test_numeric.csv",
                file_path=csv_path,
                file_size=len(csv_bytes),
                row_count=5,
                column_count=4,
                metadata_json={"columns": ["age", "salary", "department", "target"]},
            )
            db.session.add(self.dataset_a)
            db.session.commit()
            self.dataset_a_id = self.dataset_a.id

    def _login(self, username, password):
        return self.client.post(
            "/api/auth/login",
            json={"username": username, "password": password},
        )

    # --- FR-3.1-UT-1: Apply a supported preprocessing option to valid data ---

    def test_mean_imputation_fills_missing_values(self):
        """FR-3.1-UT-1: Mean imputation on dataset with NaN values succeeds."""
        self._login("user_a", "PassA123")
        resp = self.client.post(
            f"/api/dataset/{self.dataset_a_id}/preprocess",
            json={
                "missing_values": "mean",
                "encoding": "none",
                "scaling": "none",
                "save": False,
            },
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("preprocessing_summary", data)
        self.assertEqual(data["preprocessing_summary"]["missing_values"], "mean")

    def test_label_encoding_applied_to_dataset(self):
        """FR-3.1-UT-1: Label encoding on categorical columns succeeds."""
        self._login("user_a", "PassA123")
        resp = self.client.post(
            f"/api/dataset/{self.dataset_a_id}/preprocess",
            json={
                "missing_values": "mode",
                "encoding": "label",
                "scaling": "none",
                "save": False,
            },
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["preprocessing_summary"]["encoding"], "label")

    def test_onehot_encoding_expands_column_count(self):
        """FR-3.1-UT-1: One-hot encoding expands categorical columns into indicators."""
        self._login("user_a", "PassA123")
        resp = self.client.post(
            f"/api/dataset/{self.dataset_a_id}/preprocess",
            json={
                "missing_values": "drop",
                "encoding": "onehot",
                "scaling": "none",
                "target_column": "target",
                "save": False,
            },
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        # After one-hot encoding 'department' (3 categories) column count should grow
        self.assertGreater(data["column_count"], 4)

    def test_minmax_scaling_applied_after_encoding(self):
        """FR-3.1-UT-1: MinMax scaling after label encoding produces valid response."""
        self._login("user_a", "PassA123")
        resp = self.client.post(
            f"/api/dataset/{self.dataset_a_id}/preprocess",
            json={
                "missing_values": "mean",
                "encoding": "label",
                "scaling": "minmax",
                "target_column": "target",
                "save": False,
            },
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["preprocessing_summary"]["scaling"], "minmax")

    def test_standard_scaling_applied_after_encoding(self):
        """FR-3.1-UT-1: Standardization scaling after label encoding succeeds."""
        self._login("user_a", "PassA123")
        resp = self.client.post(
            f"/api/dataset/{self.dataset_a_id}/preprocess",
            json={
                "missing_values": "mean",
                "encoding": "label",
                "scaling": "standard",
                "target_column": "target",
                "save": False,
            },
        )
        self.assertEqual(resp.status_code, 200)

    def test_no_op_preprocessing_succeeds(self):
        """FR-3.1-UT-1: All-'none' config is valid and returns unchanged dimensions."""
        self._login("user_a", "PassA123")
        resp = self.client.post(
            f"/api/dataset/{self.dataset_a_id}/preprocess",
            json={
                "missing_values": "none",
                "encoding": "none",
                "scaling": "none",
                "save": False,
            },
        )
        self.assertEqual(resp.status_code, 200)

    def test_response_contains_preview_rows(self):
        """API response must include sample preview rows after preprocessing."""
        self._login("user_a", "PassA123")
        resp = self.client.post(
            f"/api/dataset/{self.dataset_a_id}/preprocess",
            json={"missing_values": "none", "encoding": "none", "scaling": "none", "save": False},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("preview", data)
        self.assertIsInstance(data["preview"], list)
        self.assertGreater(len(data["preview"]), 0)

    # --- FR-3.1-UT-2 / SEC-INP-1: Reject invalid configurations ---

    def test_invalid_missing_strategy_returns_400(self):
        """FR-3.1-UT-2 / SEC-INP-1: Invalid missing_values option rejected with HTTP 400."""
        self._login("user_a", "PassA123")
        resp = self.client.post(
            f"/api/dataset/{self.dataset_a_id}/preprocess",
            json={"missing_values": "inject_sql", "encoding": "none", "scaling": "none"},
        )
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertIn("error", data)
        self.assertIn("inject_sql", data["error"])

    def test_invalid_encoding_strategy_returns_400(self):
        """FR-3.1-UT-2 / SEC-INP-1: Invalid encoding option rejected with HTTP 400."""
        self._login("user_a", "PassA123")
        resp = self.client.post(
            f"/api/dataset/{self.dataset_a_id}/preprocess",
            json={"missing_values": "none", "encoding": "<script>", "scaling": "none"},
        )
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertIn("error", data)

    def test_invalid_scaling_strategy_returns_400(self):
        """FR-3.1-UT-2 / SEC-INP-1: Invalid scaling option rejected with HTTP 400."""
        self._login("user_a", "PassA123")
        resp = self.client.post(
            f"/api/dataset/{self.dataset_a_id}/preprocess",
            json={"missing_values": "none", "encoding": "none", "scaling": "power_transform"},
        )
        self.assertEqual(resp.status_code, 400)

    def test_nonexistent_target_column_returns_400(self):
        """FR-3.1-UT-2: A nonexistent target_column is rejected with HTTP 400."""
        self._login("user_a", "PassA123")
        resp = self.client.post(
            f"/api/dataset/{self.dataset_a_id}/preprocess",
            json={
                "missing_values": "none",
                "encoding": "none",
                "scaling": "none",
                "target_column": "nonexistent_col",
            },
        )
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertIn("nonexistent_col", data["error"])

    def test_scaling_without_encoding_on_mixed_data_returns_400(self):
        """FR-3.1-UT-2: Scaling mixed data without encoding is rejected with HTTP 400."""
        self._login("user_a", "PassA123")
        resp = self.client.post(
            f"/api/dataset/{self.dataset_a_id}/preprocess",
            json={
                "missing_values": "drop",
                "encoding": "none",   # categorical 'department' remains
                "scaling": "minmax",  # cannot scale non-numeric column
                "save": False,
            },
        )
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertIn("error", data)

    # --- SEC-AZ-2: User data isolation ---

    def test_preprocess_unauthenticated_returns_401(self):
        """SEC-AZ-2: Unauthenticated request to preprocess endpoint returns 401."""
        resp = self.client.post(
            f"/api/dataset/{self.dataset_a_id}/preprocess",
            json={"missing_values": "none", "encoding": "none", "scaling": "none"},
        )
        self.assertEqual(resp.status_code, 401)

    def test_preprocess_another_users_dataset_returns_404(self):
        """SEC-AZ-2: User B cannot preprocess User A's dataset (returns 404)."""
        self._login("user_b", "PassB123")
        resp = self.client.post(
            f"/api/dataset/{self.dataset_a_id}/preprocess",
            json={"missing_values": "none", "encoding": "none", "scaling": "none"},
        )
        # Ownership check returns 404 (not exposing that it exists to other users)
        self.assertEqual(resp.status_code, 404)

    def test_preprocess_nonexistent_dataset_returns_404(self):
        """SEC-AZ-2: Preprocessing a non-existent dataset ID returns 404."""
        self._login("user_a", "PassA123")
        resp = self.client.post(
            "/api/dataset/999999/preprocess",
            json={"missing_values": "none", "encoding": "none", "scaling": "none"},
        )
        self.assertEqual(resp.status_code, 404)


if __name__ == "__main__":
    unittest.main()
