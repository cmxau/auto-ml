import pandas as pd
import pytest

from app.services.eda_service import compute_eda_charts


def make_df():
    return pd.DataFrame({
        "age": [25, 30, None, 22, 35, 28, 45, 33, 27, 40],
        "salary": [50000.0, 60000.0, 55000.0, 48000.0, 70000.0,
                   52000.0, 80000.0, 63000.0, 49000.0, 72000.0],
        "city": ["NYC", "LA", "NYC", "SF", "LA", "NYC", "SF", "LA", "NYC", "SF"],
        "churn": ["No", "Yes", "No", "No", "Yes", "No", "Yes", "No", "No", "Yes"],
    })


SAMPLE_PROFILE = {
    "columns": [
        {"column_name": "age", "data_type": "numeric", "missing_count": 1},
        {"column_name": "salary", "data_type": "numeric", "missing_count": 0},
        {"column_name": "city", "data_type": "categorical", "missing_count": 0},
        {"column_name": "churn", "data_type": "categorical", "missing_count": 0},
    ]
}


def test_compute_eda_returns_list_of_charts():
    result = compute_eda_charts(make_df(), SAMPLE_PROFILE)
    assert isinstance(result, list)
    assert len(result) > 0


def test_missing_heatmap_included():
    charts = compute_eda_charts(make_df(), SAMPLE_PROFILE)
    types = [c["type"] for c in charts]
    assert "missing_heatmap" in types


def test_histogram_included_for_numeric():
    charts = compute_eda_charts(make_df(), SAMPLE_PROFILE)
    histogram_cols = [c["column"] for c in charts if c["type"] == "histogram"]
    assert "age" in histogram_cols
    assert "salary" in histogram_cols


def test_bar_chart_included_for_categorical():
    charts = compute_eda_charts(make_df(), SAMPLE_PROFILE)
    bar_cols = [c["column"] for c in charts if c["type"] == "bar_chart"]
    assert "city" in bar_cols
    assert "churn" in bar_cols


def test_correlation_matrix_included_when_two_or_more_numeric():
    charts = compute_eda_charts(make_df(), SAMPLE_PROFILE)
    types = [c["type"] for c in charts]
    assert "correlation_matrix" in types


def test_histogram_data_has_bins_and_counts():
    charts = compute_eda_charts(make_df(), SAMPLE_PROFILE)
    hist = next(c for c in charts if c["type"] == "histogram" and c["column"] == "salary")
    assert "bins" in hist["data"]
    assert "counts" in hist["data"]
    assert len(hist["data"]["bins"]) == len(hist["data"]["counts"]) + 1


def test_bar_chart_data_has_labels_and_counts():
    charts = compute_eda_charts(make_df(), SAMPLE_PROFILE)
    bar = next(c for c in charts if c["type"] == "bar_chart" and c["column"] == "city")
    assert "labels" in bar["data"]
    assert "counts" in bar["data"]
    assert len(bar["data"]["labels"]) == len(bar["data"]["counts"])


def test_correlation_matrix_is_square():
    charts = compute_eda_charts(make_df(), SAMPLE_PROFILE)
    corr = next(c for c in charts if c["type"] == "correlation_matrix")
    cols = corr["data"]["columns"]
    matrix = corr["data"]["matrix"]
    assert len(matrix) == len(cols)
    for row in matrix:
        assert len(row) == len(cols)


def test_missing_heatmap_reports_age_missing():
    charts = compute_eda_charts(make_df(), SAMPLE_PROFILE)
    heatmap = next(c for c in charts if c["type"] == "missing_heatmap")
    age_item = next(item for item in heatmap["data"] if item["column"] == "age")
    assert age_item["missing_count"] == 1
