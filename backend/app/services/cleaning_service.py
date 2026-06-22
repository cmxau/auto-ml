import math
import operator as op
from typing import Any, Dict, List

import pandas as pd


_FILTER_OPS = {
    "lt": op.lt, "gt": op.gt, "le": op.le,
    "ge": op.ge, "eq": op.eq, "ne": op.ne,
}

_DERIVE_OPS = {
    "add": op.add, "subtract": op.sub,
    "multiply": op.mul, "divide": op.truediv,
}


def _require_column(df: pd.DataFrame, col: str) -> None:
    if col not in df.columns:
        raise ValueError(f"Column '{col}' not found in dataset")


def _serialize_sample(df: pd.DataFrame, n: int = 5) -> List[Dict[str, Any]]:
    rows = df.head(n).to_dict(orient="records")

    def _clean(v: Any) -> Any:
        if isinstance(v, float) and math.isnan(v):
            return None
        return v

    return [{k: _clean(val) for k, val in row.items()} for row in rows]


def apply_action(df: pd.DataFrame, action_type: str, parameters: dict) -> pd.DataFrame:
    df = df.copy()

    if action_type == "drop_column":
        col = parameters["column"]
        _require_column(df, col)
        return df.drop(columns=[col])

    elif action_type == "fill_missing":
        col = parameters["column"]
        _require_column(df, col)
        method = parameters.get("method", "median")
        if method == "median":
            df[col] = df[col].fillna(df[col].median())
        elif method == "mean":
            df[col] = df[col].fillna(df[col].mean())
        elif method == "mode":
            mode_vals = df[col].mode()
            df[col] = df[col].fillna(mode_vals.iloc[0] if len(mode_vals) else None)
        elif method == "constant":
            df[col] = df[col].fillna(parameters["value"])
        else:
            raise ValueError(f"Unknown fill method '{method}'")
        return df

    elif action_type == "remove_duplicates":
        subset = parameters.get("subset") or None
        return df.drop_duplicates(subset=subset).reset_index(drop=True)

    elif action_type == "filter_rows":
        col = parameters["column"]
        _require_column(df, col)
        operator_key = parameters["operator"]
        if operator_key not in _FILTER_OPS:
            raise ValueError(f"Unknown operator '{operator_key}'")
        value = parameters["value"]
        mask = _FILTER_OPS[operator_key](df[col], value)
        return df[~mask].reset_index(drop=True)

    elif action_type == "encode_categorical":
        col = parameters["column"]
        _require_column(df, col)
        method = parameters.get("method", "onehot")
        if method == "onehot":
            dummies = pd.get_dummies(df[col], prefix=col, dtype=int)
            df = pd.concat([df.drop(columns=[col]), dummies], axis=1)
        elif method == "label":
            df[col] = df[col].astype("category").cat.codes
        else:
            raise ValueError(f"Unknown encode method '{method}'")
        return df

    elif action_type == "scale_numeric":
        col = parameters["column"]
        _require_column(df, col)
        method = parameters.get("method", "standard")
        series = df[col].astype(float)
        if method == "standard":
            mean, std = series.mean(), series.std()
            df[col] = (series - mean) / std if std != 0 else series - mean
        elif method == "minmax":
            min_val, max_val = series.min(), series.max()
            df[col] = (series - min_val) / (max_val - min_val) if max_val != min_val else series * 0
        else:
            raise ValueError(f"Unknown scale method '{method}'")
        return df

    elif action_type == "convert_type":
        col = parameters["column"]
        _require_column(df, col)
        dtype = parameters["dtype"]
        if dtype == "datetime":
            df[col] = pd.to_datetime(df[col], errors="coerce")
        else:
            df[col] = df[col].astype(dtype, errors="ignore")
        return df

    elif action_type == "clip_outliers":
        col = parameters["column"]
        _require_column(df, col)
        method = parameters.get("method", "iqr")
        threshold = float(parameters.get("threshold", 1.5 if method == "iqr" else 3.0))
        series = df[col].astype(float)
        if method == "iqr":
            q1, q3 = series.quantile(0.25), series.quantile(0.75)
            iqr = q3 - q1
            lower, upper = q1 - threshold * iqr, q3 + threshold * iqr
            df[col] = series.clip(lower, upper)
        elif method == "zscore":
            mean, std = series.mean(), series.std()
            if std == 0:
                return df
            lower = mean - threshold * std
            upper = mean + threshold * std
            df[col] = series.clip(lower, upper)
        else:
            raise ValueError(f"Unknown clip method '{method}'")
        return df

    elif action_type == "derive_feature":
        new_col = parameters["new_column"]
        left_col = parameters["left_column"]
        _require_column(df, left_col)
        operator_key = parameters["operator"]
        if operator_key not in _DERIVE_OPS:
            raise ValueError(f"Unknown derive operator '{operator_key}'")
        left = df[left_col].astype(float)
        if "right_column" in parameters:
            _require_column(df, parameters["right_column"])
            right = df[parameters["right_column"]].astype(float)
        else:
            right = float(parameters["right_value"])
        df[new_col] = _DERIVE_OPS[operator_key](left, right)
        return df

    else:
        raise ValueError(f"Unknown action_type '{action_type}'")


def preview_action(df: pd.DataFrame, action_type: str, parameters: dict) -> Dict[str, Any]:
    cols_before = list(df.columns)
    rows_before = len(df)

    result_df = apply_action(df.copy(), action_type, parameters)

    cols_after = list(result_df.columns)
    rows_after = len(result_df)

    return {
        "rows_before": rows_before,
        "rows_after": rows_after,
        "columns_before": len(cols_before),
        "columns_after": len(cols_after),
        "columns_added": [c for c in cols_after if c not in cols_before],
        "columns_removed": [c for c in cols_before if c not in cols_after],
        "sample_rows": _serialize_sample(result_df),
    }
