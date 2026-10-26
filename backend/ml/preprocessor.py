# Machine Learning Preprocessing Module
#
# TODO: US-14: Implement data preprocessing (Assigned to: @aryannang123)
# TODO: US-15: Implement target column selection (Assigned to: @abhishekdeene-eng)
# TODO: US-16: Implement train-test split configuration (Assigned to: @nidhipoojamrutha20)

import math
from numbers import Real

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

class DataPreprocessor:
    """Preprocesses tabular dataset before training."""

    @staticmethod
    def inspect(df):
        """Inspect columns, null counts, and data types (US-09 & US-13)."""
        pass

    @staticmethod
    def handle_missing_values(df):
        """Impute or drop missing data (US-14)."""
        pass

    @staticmethod
    def encode_features(X):
        """Encode categorical features (US-14)."""
        pass

    @staticmethod
    def split(X, y, test_size=0.2, random_state=42, stratify=None):
        """Split aligned samples, defaulting to 80% train and 20% test."""
        if isinstance(test_size, bool) or not isinstance(test_size, Real):
            raise ValueError("test_size must be a finite number greater than 0 and less than 1.")
        test_size = float(test_size)
        if not math.isfinite(test_size) or not 0 < test_size < 1:
            raise ValueError("test_size must be a finite number greater than 0 and less than 1.")

        try:
            sample_count = len(X)
            target_count = len(y)
        except TypeError as exc:
            raise ValueError("Features and target must be sized collections.") from exc
        if sample_count != target_count:
            raise ValueError("Features and target must contain the same number of samples.")
        if sample_count < 2:
            raise ValueError("At least 2 samples are required to create training and testing partitions.")

        test_count = math.ceil(sample_count * test_size)
        train_count = sample_count - test_count
        if test_count < 1 or train_count < 1:
            raise ValueError(
                "The selected split leaves no samples in the training or testing partition. "
                "Choose a different ratio or provide more data."
            )

        if stratify is not None:
            if len(stratify) != sample_count:
                raise ValueError("Stratification labels must match the number of samples.")
            class_count = len(pd.unique(stratify))
            if test_count < class_count or train_count < class_count:
                raise ValueError(
                    "The selected split does not leave enough training and testing samples "
                    "to represent every target class. Choose a different ratio or provide more data."
                )

        try:
            return train_test_split(
                X,
                y,
                test_size=test_size,
                random_state=random_state,
                stratify=stratify,
            )
        except ValueError as exc:
            raise ValueError(
                "The selected split cannot produce valid training and testing partitions. "
                "Check the sample count and target class distribution."
            ) from exc

    @staticmethod
    def build_pipeline(X_train, estimator, scale_numeric=False):
        """Build preprocessing that is fitted only on the training partition."""
        numeric_columns = list(X_train.select_dtypes(include="number").columns)
        categorical_columns = [column for column in X_train.columns if column not in numeric_columns]
        transformers = []
        if numeric_columns:
            numeric_steps = [("imputer", SimpleImputer(strategy="median"))]
            if scale_numeric:
                numeric_steps.append(("scaler", StandardScaler()))
            transformers.append(("numeric", Pipeline(numeric_steps), numeric_columns))
        if categorical_columns:
            categorical_steps = Pipeline([
                ("imputer", SimpleImputer(strategy="most_frequent")),
                ("encoder", OneHotEncoder(handle_unknown="ignore")),
            ])
            transformers.append(("categorical", categorical_steps, categorical_columns))
        if not transformers:
            raise ValueError("Select at least one usable feature column for training.")
        return Pipeline([
            ("preprocessor", ColumnTransformer(transformers)),
            ("estimator", estimator),
        ])
