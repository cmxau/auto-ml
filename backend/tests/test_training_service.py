import io

import numpy as np
import pandas as pd
import pytest

from app.services.training_service import (
    build_model,
    compute_classification_metrics,
    compute_regression_metrics,
    extract_feature_importance,
    prepare_features,
    serialize_model,
)


def make_classification_df():
    np.random.seed(42)
    return pd.DataFrame({
        "age": np.random.randint(18, 65, 100).astype(float),
        "salary": np.random.uniform(30000, 100000, 100),
        "city": np.random.choice(["NYC", "LA", "SF"], 100),
        "churn": np.random.choice(["Yes", "No"], 100),
    })


def make_regression_df():
    np.random.seed(42)
    return pd.DataFrame({
        "rooms": np.random.randint(1, 6, 100).astype(float),
        "area": np.random.uniform(500, 3000, 100),
        "price": np.random.uniform(100000, 1000000, 100),
    })


# --- prepare_features ---

def test_prepare_features_drops_target():
    df = make_classification_df()
    X, y = prepare_features(df, "churn")
    assert "churn" not in X.columns
    assert len(y) == len(df)


def test_prepare_features_encodes_categorical():
    df = make_classification_df()
    X, _ = prepare_features(df, "churn")
    assert "city" in X.columns
    assert pd.api.types.is_numeric_dtype(X["city"])


def test_prepare_features_fills_nan():
    df = make_classification_df()
    df.loc[0, "age"] = np.nan
    X, _ = prepare_features(df, "churn")
    assert X["age"].isna().sum() == 0


def test_prepare_features_keeps_only_numeric():
    df = make_classification_df()
    X, _ = prepare_features(df, "churn")
    assert all(pd.api.types.is_numeric_dtype(X[c]) for c in X.columns)


# --- build_model ---

def test_build_model_logistic_regression():
    from sklearn.linear_model import LogisticRegression
    assert isinstance(build_model("logistic_regression"), LogisticRegression)


def test_build_model_random_forest():
    from sklearn.ensemble import RandomForestClassifier
    assert isinstance(build_model("random_forest"), RandomForestClassifier)


def test_build_model_xgboost():
    from xgboost import XGBClassifier
    assert isinstance(build_model("xgboost"), XGBClassifier)


def test_build_model_linear_regression():
    from sklearn.linear_model import LinearRegression
    assert isinstance(build_model("linear_regression"), LinearRegression)


def test_build_model_random_forest_regressor():
    from sklearn.ensemble import RandomForestRegressor
    assert isinstance(build_model("random_forest_regressor"), RandomForestRegressor)


def test_build_model_xgboost_regressor():
    from xgboost import XGBRegressor
    assert isinstance(build_model("xgboost_regressor"), XGBRegressor)


def test_build_model_unknown_raises():
    with pytest.raises(ValueError, match="Unknown model_type"):
        build_model("magic_model")


# --- compute_classification_metrics ---

def test_compute_classification_metrics_keys():
    y_true = np.array([0, 1, 0, 1, 1])
    y_pred = np.array([0, 1, 0, 0, 1])
    m = compute_classification_metrics(y_true, y_pred)
    for key in ("accuracy", "f1_score", "precision", "recall"):
        assert key in m
        assert 0.0 <= m[key] <= 1.0


def test_compute_classification_metrics_with_proba():
    y_true = np.array([0, 1, 0, 1])
    y_pred = np.array([0, 1, 0, 1])
    y_prob = np.array([[0.9, 0.1], [0.2, 0.8], [0.8, 0.2], [0.1, 0.9]])
    m = compute_classification_metrics(y_true, y_pred, y_prob)
    assert "roc_auc" in m


# --- compute_regression_metrics ---

def test_compute_regression_metrics_keys():
    y_true = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    y_pred = np.array([1.1, 2.1, 2.9, 4.2, 4.8])
    m = compute_regression_metrics(y_true, y_pred)
    for key in ("r2_score", "rmse", "mae", "mse"):
        assert key in m


def test_compute_regression_metrics_perfect():
    y = np.array([1.0, 2.0, 3.0])
    m = compute_regression_metrics(y, y)
    assert m["r2_score"] == pytest.approx(1.0)
    assert m["rmse"] == pytest.approx(0.0)


# --- extract_feature_importance ---

def test_extract_feature_importance_tree_model():
    from sklearn.preprocessing import LabelEncoder
    df = make_classification_df()
    X, y = prepare_features(df, "churn")
    le = LabelEncoder()
    y_enc = le.fit_transform(y.astype(str))
    model = build_model("random_forest")
    model.fit(X, y_enc)
    imp = extract_feature_importance(model, list(X.columns))
    assert len(imp) == len(X.columns)
    assert imp[0]["importance"] >= imp[-1]["importance"]


def test_extract_feature_importance_linear_model():
    df = make_regression_df()
    X, y = prepare_features(df, "price")
    model = build_model("linear_regression")
    model.fit(X, y)
    imp = extract_feature_importance(model, list(X.columns))
    assert len(imp) == len(X.columns)
    values = [i["importance"] for i in imp]
    assert values == sorted(values, reverse=True)


# --- serialize_model ---

def test_serialize_model_returns_bytes():
    model = build_model("logistic_regression")
    result = serialize_model(model)
    assert isinstance(result, bytes)
    assert len(result) > 0
