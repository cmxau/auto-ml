from typing import Any, Dict, List

import pandas as pd


def _infer_type(series: pd.Series) -> str:
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"
    # Categorical: <= 60% unique values relative to non-null count
    # (text/ID-like columns tend to be near 100% unique)
    non_null_count = series.count()
    if non_null_count > 0 and (series.nunique() / non_null_count) <= 0.6:
        return "categorical"
    return "text"


def profile_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
    row_count = len(df)
    column_count = len(df.columns)
    duplicate_row_count = int(df.duplicated().sum())

    columns: List[Dict[str, Any]] = []
    numeric_count = 0
    categorical_count = 0

    for col in df.columns:
        series = df[col]
        dtype = _infer_type(series)
        missing_count = int(series.isna().sum())
        unique_count = int(series.nunique())
        non_null_count = int(series.count())
        high_cardinality = dtype in ("text", "categorical") and unique_count > 50

        col_profile: Dict[str, Any] = {
            "column_name": col,
            "data_type": dtype,
            "missing_count": missing_count,
            "unique_count": unique_count,
            "high_cardinality_flag": high_cardinality,
            "mean_value": None,
            "std_value": None,
            "min_value": None,
            "max_value": None,
            "top_values": [],
            "example_values": [str(v) for v in series.dropna().head(5).tolist()],
        }

        if dtype == "numeric":
            numeric_count += 1
            if non_null_count > 0:
                col_profile["mean_value"] = float(series.mean())
                col_profile["min_value"] = float(series.min())
                col_profile["max_value"] = float(series.max())
            if non_null_count > 1:
                col_profile["std_value"] = float(series.std())
        elif dtype == "categorical":
            categorical_count += 1
            vc = series.value_counts().head(10)
            col_profile["top_values"] = [
                {"value": str(v), "count": int(c)} for v, c in vc.items()
            ]

        columns.append(col_profile)

    missing_value_count = sum(c["missing_count"] for c in columns)

    return {
        "row_count": row_count,
        "column_count": column_count,
        "duplicate_row_count": duplicate_row_count,
        "missing_value_count": missing_value_count,
        "numeric_column_count": numeric_count,
        "categorical_column_count": categorical_count,
        "columns": columns,
    }
