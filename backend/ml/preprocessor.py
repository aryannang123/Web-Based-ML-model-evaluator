import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler

class DataPreprocessor:
    """Handles dataset inspection, cleaning, encoding, and train-test splitting."""

    @staticmethod
    def inspect_dataset(df: pd.DataFrame) -> dict:
        """Return dataset overview, columns, missing value counts, and data types."""
        columns_info = []
        for col in df.columns:
            columns_info.append({
                "name": col,
                "dtype": str(df[col].dtype),
                "null_count": int(df[col].isnull().sum()),
                "unique_count": int(df[col].nunique()),
                "sample_values": df[col].dropna().head(3).tolist()
            })
        return {
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "columns": columns_info
        }

    @staticmethod
    def detect_task_type(series: pd.Series) -> str:
        """Infer whether problem is classification or regression."""
        if series.dtype == "object" or series.nunique() <= 10:
            return "classification"
        return "regression"

    @classmethod
    def prepare_data(cls, df: pd.DataFrame, target_col: str, test_size: float = 0.2, random_state: int = 42):
        """Clean nulls, encode categoricals, split features and target."""
        if target_col not in df.columns:
            raise ValueError(f"Target column '{target_col}' not found in dataset.")

        # Drop rows where target is missing
        clean_df = df.dropna(subset=[target_col]).copy()

        # Separate X and y
        X = clean_df.drop(columns=[target_col])
        y = clean_df[target_col]

        # Handle numeric and categorical columns
        numeric_cols = X.select_dtypes(include=[np.number]).columns
        categorical_cols = X.select_dtypes(exclude=[np.number]).columns

        # Impute numeric missing values with median
        for col in numeric_cols:
            if X[col].isnull().sum() > 0:
                X[col] = X[col].fillna(X[col].median())

        # Impute and One-Hot / Label encode categorical features
        for col in categorical_cols:
            X[col] = X[col].fillna(X[col].mode()[0] if not X[col].mode().empty else "missing")
            le = LabelEncoder()
            X[col] = le.fit_transform(X[col].astype(str))

        # Scale features
        scaler = StandardScaler()
        if len(X.columns) > 0:
            X_scaled = scaler.fit_transform(X)
        else:
            X_scaled = X.values

        # Encode target if classification
        task_type = cls.detect_task_type(y)
        if task_type == "classification" and (y.dtype == "object" or not np.issubdtype(y.dtype, np.number)):
            target_encoder = LabelEncoder()
            y_encoded = target_encoder.fit_transform(y.astype(str))
        else:
            y_encoded = y.values

        # Split
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y_encoded, test_size=test_size, random_state=random_state
        )

        return {
            "X_train": X_train,
            "X_test": X_test,
            "y_train": y_train,
            "y_test": y_test,
            "task_type": task_type,
            "feature_names": list(X.columns)
        }
