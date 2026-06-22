import math
import pandas as pd
import pytest

from app.services.cleaning_service import apply_action, preview_action


def base_df():
    return pd.DataFrame({
        "age":    [25, 30, None, 17, 35, 28, 45, 33, 27, 40],
        "salary": [50000.0, 60000.0, 55000.0, 48000.0, 70000.0,
                   52000.0, 80000.0, 63000.0, 49000.0, 72000.0],
        "city":   ["NYC", "LA", "NYC", "SF", "LA", "NYC", "SF", "LA", "NYC", "SF"],
        "label":  ["No", "Yes", "No", "No", "Yes", "No", "Yes", "No", "No", "Yes"],
        "cust_id": [f"C{i:04d}" for i in range(10)],
    })


def test_drop_column_removes_column():
    df = apply_action(base_df(), "drop_column", {"column": "cust_id"})
    assert "cust_id" not in df.columns


def test_drop_column_raises_on_missing_column():
    with pytest.raises(ValueError, match="Column 'nonexistent' not found"):
        apply_action(base_df(), "drop_column", {"column": "nonexistent"})


def test_fill_missing_median():
    df = apply_action(base_df(), "fill_missing", {"column": "age", "method": "median"})
    assert df["age"].isna().sum() == 0
    assert df.loc[2, "age"] == base_df()["age"].median()


def test_fill_missing_mean():
    df = apply_action(base_df(), "fill_missing", {"column": "age", "method": "mean"})
    assert df["age"].isna().sum() == 0


def test_fill_missing_mode():
    df = apply_action(base_df(), "fill_missing", {"column": "city", "method": "mode"})
    assert df["city"].isna().sum() == 0


def test_fill_missing_constant():
    df = apply_action(base_df(), "fill_missing", {"column": "age", "method": "constant", "value": 0})
    assert df.loc[2, "age"] == 0


def test_remove_duplicates_drops_exact_copies():
    dup = pd.concat([base_df(), base_df().iloc[:2]], ignore_index=True)
    df = apply_action(dup, "remove_duplicates", {})
    assert len(df) == len(base_df())


def test_filter_rows_lt_removes_matching():
    df = apply_action(base_df(), "filter_rows", {"column": "age", "operator": "lt", "value": 18})
    assert all(v >= 18 for v in df["age"].dropna())


def test_filter_rows_eq_removes_matching():
    df = apply_action(base_df(), "filter_rows", {"column": "city", "operator": "eq", "value": "SF"})
    assert "SF" not in df["city"].values


def test_encode_categorical_onehot_expands_columns():
    df = apply_action(base_df(), "encode_categorical", {"column": "city", "method": "onehot"})
    assert "city" not in df.columns
    assert any(c.startswith("city_") for c in df.columns)


def test_encode_categorical_label_is_numeric():
    df = apply_action(base_df(), "encode_categorical", {"column": "label", "method": "label"})
    assert pd.api.types.is_numeric_dtype(df["label"])


def test_scale_standard_mean_near_zero():
    df = apply_action(base_df(), "scale_numeric", {"column": "salary", "method": "standard"})
    assert abs(df["salary"].mean()) < 1e-9


def test_scale_minmax_in_unit_range():
    df = apply_action(base_df(), "scale_numeric", {"column": "salary", "method": "minmax"})
    assert df["salary"].min() >= 0.0 - 1e-9
    assert df["salary"].max() <= 1.0 + 1e-9


def test_convert_type_to_str():
    df = apply_action(base_df(), "convert_type", {"column": "age", "dtype": "str"})
    assert df["age"].dtype == object


def test_convert_type_to_float():
    df_in = base_df().copy()
    df_in["age"] = df_in["age"].fillna(0).astype(int)
    df = apply_action(df_in, "convert_type", {"column": "age", "dtype": "float"})
    assert pd.api.types.is_float_dtype(df["age"])


def test_clip_outliers_iqr_keeps_all_rows():
    df = apply_action(base_df(), "clip_outliers", {"column": "salary", "method": "iqr"})
    assert len(df) == len(base_df())


def test_clip_outliers_zscore_keeps_all_rows():
    df = apply_action(base_df(), "clip_outliers", {"column": "salary", "method": "zscore"})
    assert len(df) == len(base_df())


def test_derive_feature_add():
    df = apply_action(base_df().dropna(), "derive_feature", {
        "new_column": "age_salary",
        "left_column": "age",
        "operator": "add",
        "right_value": 1000,
    })
    assert "age_salary" in df.columns
    assert df.loc[0, "age_salary"] == df.loc[0, "age"] + 1000


def test_derive_feature_column_divide():
    df = apply_action(base_df().dropna(), "derive_feature", {
        "new_column": "salary_per_age",
        "left_column": "salary",
        "operator": "divide",
        "right_column": "age",
    })
    assert "salary_per_age" in df.columns


def test_unknown_action_type_raises():
    with pytest.raises(ValueError, match="Unknown action_type"):
        apply_action(base_df(), "explode_everything", {})


def test_preview_returns_before_after_stats():
    result = preview_action(base_df(), "drop_column", {"column": "cust_id"})
    assert result["columns_before"] == 5
    assert result["columns_after"] == 4
    assert "cust_id" in result["columns_removed"]
    assert result["rows_before"] == result["rows_after"]


def test_preview_filter_rows_reduces_rows():
    result = preview_action(base_df(), "filter_rows", {
        "column": "age", "operator": "lt", "value": 18
    })
    assert result["rows_after"] < result["rows_before"]


def test_preview_sample_rows_serializable():
    import json
    result = preview_action(base_df(), "fill_missing", {"column": "age", "method": "median"})
    json.dumps(result["sample_rows"])  # must not raise
