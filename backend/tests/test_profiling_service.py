import pandas as pd
import pytest

from app.services.profiling_service import profile_dataframe


def make_df():
    return pd.DataFrame({
        "age": [25, 30, None, 22, 35],
        "salary": [50000.0, 60000.0, 55000.0, 48000.0, 70000.0],
        "city": ["NYC", "LA", "NYC", "SF", "LA"],
        "name": ["Alice", "Bob", "Charlie", "Dave", "Eve"],
    })


def test_profile_shape():
    df = make_df()
    result = profile_dataframe(df)
    assert result["row_count"] == 5
    assert result["column_count"] == 4


def test_profile_missing_values():
    df = make_df()
    result = profile_dataframe(df)
    age_col = next(c for c in result["columns"] if c["column_name"] == "age")
    assert age_col["missing_count"] == 1


def test_profile_numeric_stats():
    df = make_df()
    result = profile_dataframe(df)
    salary_col = next(c for c in result["columns"] if c["column_name"] == "salary")
    assert salary_col["data_type"] == "numeric"
    assert abs(salary_col["mean_value"] - 56600.0) < 1


def test_profile_categorical():
    df = make_df()
    result = profile_dataframe(df)
    city_col = next(c for c in result["columns"] if c["column_name"] == "city")
    assert city_col["data_type"] == "categorical"
    assert city_col["unique_count"] == 3
    top_vals = {v["value"] for v in city_col["top_values"]}
    assert "NYC" in top_vals


def test_profile_duplicate_rows():
    df = pd.DataFrame({"a": [1, 1, 2], "b": ["x", "x", "y"]})
    result = profile_dataframe(df)
    assert result["duplicate_row_count"] == 1


def test_profile_high_cardinality():
    import uuid
    df = pd.DataFrame({"id": [str(uuid.uuid4()) for _ in range(100)], "val": range(100)})
    result = profile_dataframe(df)
    id_col = next(c for c in result["columns"] if c["column_name"] == "id")
    assert id_col["high_cardinality_flag"] is True
