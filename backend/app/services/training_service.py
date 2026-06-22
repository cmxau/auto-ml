import io
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier, XGBRegressor

_CLASSIFICATION_MODELS = {
    "logistic_regression": LogisticRegression,
    "random_forest": RandomForestClassifier,
    "xgboost": XGBClassifier,
}

_REGRESSION_MODELS = {
    "linear_regression": LinearRegression,
    "random_forest_regressor": RandomForestRegressor,
    "xgboost_regressor": XGBRegressor,
}

_DEFAULT_HYPERPARAMS: Dict[str, Dict] = {
    "logistic_regression": {"max_iter": 300, "random_state": 42},
    "random_forest": {"n_estimators": 100, "random_state": 42},
    "xgboost": {"n_estimators": 100, "random_state": 42},
    "linear_regression": {},
    "random_forest_regressor": {"n_estimators": 100, "random_state": 42},
    "xgboost_regressor": {"n_estimators": 100, "random_state": 42},
}


def prepare_features(
    df: pd.DataFrame, target_column: str
) -> Tuple[pd.DataFrame, pd.Series]:
    """Drop target, encode categoricals, fill NaN. Returns (X, y)."""
    y = df[target_column].copy()
    X = df.drop(columns=[target_column]).copy()

    for col in X.select_dtypes(include=["object", "category"]).columns:
        le = LabelEncoder()
        X[col] = le.fit_transform(X[col].astype(str))

    X = X.fillna(X.median(numeric_only=True))
    X = X.fillna(0)
    X = X.select_dtypes(include=[np.number])

    return X, y


def build_model(model_type: str, hyperparameters: Optional[Dict] = None) -> Any:
    """Return an unfitted sklearn/XGBoost model."""
    defaults = _DEFAULT_HYPERPARAMS.get(model_type, {})
    params = {**defaults, **(hyperparameters or {})}

    if model_type in _CLASSIFICATION_MODELS:
        return _CLASSIFICATION_MODELS[model_type](**params)
    if model_type in _REGRESSION_MODELS:
        return _REGRESSION_MODELS[model_type](**params)
    raise ValueError(f"Unknown model_type '{model_type}'")


def compute_classification_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_prob: Optional[np.ndarray] = None,
) -> Dict[str, float]:
    metrics: Dict[str, float] = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "f1_score": float(f1_score(y_true, y_pred, average="weighted", zero_division=0)),
        "precision": float(precision_score(y_true, y_pred, average="weighted", zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, average="weighted", zero_division=0)),
    }
    if y_prob is not None and len(np.unique(y_true)) == 2:
        try:
            metrics["roc_auc"] = float(roc_auc_score(y_true, y_prob[:, 1]))
        except Exception:
            pass
    return metrics


def compute_regression_metrics(
    y_true: np.ndarray, y_pred: np.ndarray
) -> Dict[str, float]:
    mse = float(mean_squared_error(y_true, y_pred))
    return {
        "r2_score": float(r2_score(y_true, y_pred)),
        "rmse": float(np.sqrt(mse)),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "mse": mse,
    }


def extract_feature_importance(
    model: Any, feature_names: List[str]
) -> List[Dict[str, float]]:
    """Extract feature importances from a fitted model. Sorted descending."""
    importances = None

    if hasattr(model, "feature_importances_"):
        importances = np.asarray(model.feature_importances_, dtype=float)
    elif hasattr(model, "coef_"):
        coef = np.asarray(model.coef_, dtype=float)
        importances = np.abs(coef).mean(axis=0) if coef.ndim > 1 else np.abs(coef)

    if importances is None:
        return []

    results = [
        {"feature": name, "importance": float(imp)}
        for name, imp in zip(feature_names, importances)
    ]
    return sorted(results, key=lambda x: x["importance"], reverse=True)


def serialize_model(model: Any) -> bytes:
    """Serialize fitted model to bytes via joblib."""
    buf = io.BytesIO()
    joblib.dump(model, buf)
    return buf.getvalue()
