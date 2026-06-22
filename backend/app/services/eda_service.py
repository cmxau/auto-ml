from typing import Any, Dict, List

import pandas as pd


def _compute_missing_heatmap(df: pd.DataFrame) -> Dict[str, Any]:
    total = len(df)
    data = []
    for col in df.columns:
        missing = int(df[col].isna().sum())
        data.append({
            "column": col,
            "missing_count": missing,
            "missing_pct": round(missing / total * 100, 2) if total > 0 else 0.0,
        })
    return {
        "type": "missing_heatmap",
        "title": "Missing Values per Column",
        "data": data,
    }


def _compute_histogram(df: pd.DataFrame, column: str, bins: int = 20) -> Dict[str, Any]:
    series = df[column].dropna()
    if len(series) == 0:
        return {
            "type": "histogram",
            "column": column,
            "title": f"Distribution of {column}",
            "data": {"bins": [], "counts": []},
        }
    counts, bin_edges = pd.cut(series, bins=bins, retbins=True)
    count_values = counts.value_counts(sort=False).tolist()
    bin_edges_list = [round(float(e), 4) for e in bin_edges]
    return {
        "type": "histogram",
        "column": column,
        "title": f"Distribution of {column}",
        "data": {
            "bins": bin_edges_list,
            "counts": count_values,
        },
    }


def _compute_bar_chart(df: pd.DataFrame, column: str, top_n: int = 15) -> Dict[str, Any]:
    vc = df[column].value_counts().head(top_n)
    return {
        "type": "bar_chart",
        "column": column,
        "title": f"Value counts: {column}",
        "data": {
            "labels": [str(v) for v in vc.index.tolist()],
            "counts": vc.tolist(),
        },
    }


def _compute_correlation_matrix(df: pd.DataFrame, numeric_cols: List[str]) -> Dict[str, Any]:
    sub = df[numeric_cols].dropna()
    if len(sub) < 2:
        corr_data = [[1.0 if i == j else 0.0 for j in range(len(numeric_cols))]
                     for i in range(len(numeric_cols))]
    else:
        corr = sub.corr()
        corr_data = [
            [round(float(corr.loc[r, c]), 4) for c in numeric_cols]
            for r in numeric_cols
        ]
    return {
        "type": "correlation_matrix",
        "title": "Correlation Matrix",
        "data": {
            "columns": numeric_cols,
            "matrix": corr_data,
        },
    }


def compute_eda_charts(df: pd.DataFrame, profile: dict) -> List[Dict[str, Any]]:
    """Compute all EDA chart data from a DataFrame and its column profile."""
    charts: List[Dict[str, Any]] = []

    charts.append(_compute_missing_heatmap(df))

    numeric_cols: List[str] = []
    for col_profile in profile.get("columns", []):
        col = col_profile["column_name"]
        dtype = col_profile["data_type"]

        if col not in df.columns:
            continue

        if dtype == "numeric":
            numeric_cols.append(col)
            charts.append(_compute_histogram(df, col))
        elif dtype == "categorical":
            charts.append(_compute_bar_chart(df, col))

    if len(numeric_cols) >= 2:
        charts.append(_compute_correlation_matrix(df, numeric_cols))

    return charts
