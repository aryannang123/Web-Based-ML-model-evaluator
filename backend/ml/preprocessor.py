"""Safe tabular validation and leakage-free preprocessing utilities."""

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.model_selection import train_test_split


class DataPreprocessor:
    @staticmethod
    def inspect(df):
        return {
            "row_count": int(df.shape[0]),
            "column_count": int(df.shape[1]),
            "columns": [
                {
                    "name": str(column),
                    "dtype": str(df[column].dtype),
                    "missing_count": int(df[column].isna().sum()),
                    "unique_count": int(df[column].nunique(dropna=True)),
                }
                for column in df.columns
            ],
        }

    @staticmethod
    def infer_task_type(target):
        """Infer classification for categorical/low-cardinality targets."""
        if (
            pd.api.types.is_object_dtype(target)
            or pd.api.types.is_bool_dtype(target)
            or isinstance(target.dtype, pd.CategoricalDtype)
        ):
            return "classification"
        unique_count = target.nunique(dropna=True)
        if unique_count <= 20:
            return "classification"
        return "regression"

    @staticmethod
    def validate_target(df, target_column):
        if not isinstance(target_column, str) or target_column not in df.columns:
            raise ValueError("Select a target column from the uploaded dataset.")
        target = df[target_column]
        if target.isna().all() or target.nunique(dropna=True) < 2:
            raise ValueError("The target column must contain at least two values.")
        return target

    @staticmethod
    def make_transformer(X, options=None):
        options = options or {}
        missing_strategy = options.get("missing_strategy", "impute")
        encode_categorical = options.get("encode_categorical", True)
        scale_numeric = options.get("scale_numeric", True)
        numeric_columns = X.select_dtypes(include=["number"]).columns.tolist()
        categorical_columns = [
            column for column in X.columns if column not in numeric_columns
        ]
        transformers = []
        if numeric_columns:
            numeric_steps = [(
                "imputer", SimpleImputer(
                    strategy=options.get("numeric_imputer", "median"),
                    keep_empty_features=True,
                )
            )]
            if scale_numeric:
                numeric_steps.append(("scaler", StandardScaler()))
            transformers.append((
                "numeric",
                Pipeline(numeric_steps),
                numeric_columns,
            ))
        if categorical_columns:
            if not encode_categorical:
                raise ValueError(
                    "Categorical features require one-hot encoding for model training."
                )
            categorical_imputer = []
            if missing_strategy == "impute":
                categorical_imputer.append((
                    "imputer", SimpleImputer(
                        strategy="most_frequent", keep_empty_features=True
                    )
                ))
            categorical_imputer.append((
                "encoder", OneHotEncoder(handle_unknown="ignore")
            ))
            transformers.append((
                "categorical",
                Pipeline(categorical_imputer),
                categorical_columns,
            ))
        return ColumnTransformer(transformers=transformers, remainder="drop")

    @staticmethod
    def handle_missing_values(df):
        """Return a copy with missing cells filled for preview/export purposes."""
        result = df.copy()
        for column in result.columns:
            if result[column].isna().all():
                result[column] = result[column].fillna("Unknown")
            elif pd.api.types.is_numeric_dtype(result[column]):
                result[column] = result[column].fillna(result[column].median())
            else:
                mode = result[column].mode(dropna=True)
                result[column] = result[column].fillna(
                    mode.iloc[0] if not mode.empty else "Unknown"
                )
        return result

    @staticmethod
    def encode_features(X):
        transformer = DataPreprocessor.make_transformer(X)
        return transformer.fit_transform(X), transformer

    @staticmethod
    def split(X, y, test_size=0.2, random_state=42, task_type=None):
        if not 0.1 <= float(test_size) <= 0.5:
            raise ValueError("Test split must be between 10% and 50%.")
        stratify = None
        if task_type == "classification":
            counts = y.value_counts(dropna=True)
            test_rows = max(1, int(round(len(y) * float(test_size))))
            if len(counts) > 1 and counts.min() >= 2 and test_rows >= len(counts):
                stratify = y
        return train_test_split(
            X, y, test_size=float(test_size), random_state=random_state,
            stratify=stratify,
        )
