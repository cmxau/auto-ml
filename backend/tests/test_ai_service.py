import json
from unittest.mock import MagicMock, patch

import pytest

from app.services.ai_service import (
    _build_profile_summary,
    _sanitize_top_values,
    analyze_dataset,
    suggest_cleaning_actions,
    recommend_models,
)


SAMPLE_PROFILE = {
    "row_count": 1000,
    "column_count": 5,
    "missing_value_count": 30,
    "duplicate_row_count": 5,
    "numeric_column_count": 2,
    "categorical_column_count": 2,
    "columns": [
        {
            "column_name": "age",
            "data_type": "numeric",
            "missing_count": 10,
            "unique_count": 50,
            "mean_value": 35.0,
            "std_value": 12.0,
            "min_value": 18.0,
            "max_value": 75.0,
            "top_values": [],
            "example_values": ["25", "30", "22"],
            "high_cardinality_flag": False,
        },
        {
            "column_name": "churn",
            "data_type": "categorical",
            "missing_count": 0,
            "unique_count": 2,
            "mean_value": None,
            "std_value": None,
            "min_value": None,
            "max_value": None,
            "top_values": [{"value": "No", "count": 700}, {"value": "Yes", "count": 300}],
            "example_values": ["No", "Yes"],
            "high_cardinality_flag": False,
        },
        {
            "column_name": "customer_id",
            "data_type": "categorical",
            "missing_count": 0,
            "unique_count": 1000,
            "mean_value": None,
            "std_value": None,
            "min_value": None,
            "max_value": None,
            "top_values": [],
            "example_values": ["C001", "C002"],
            "high_cardinality_flag": True,
        },
        {
            "column_name": "monthly_charge",
            "data_type": "numeric",
            "missing_count": 20,
            "unique_count": 300,
            "mean_value": 65.0,
            "std_value": 30.0,
            "min_value": 10.0,
            "max_value": 150.0,
            "top_values": [],
            "example_values": ["70.0", "45.5"],
            "high_cardinality_flag": False,
        },
    ],
}


def make_mock_response(content: dict):
    mock = MagicMock()
    mock.choices[0].message.content = json.dumps(content)
    return mock


def test_build_profile_summary_contains_key_stats():
    summary = _build_profile_summary(SAMPLE_PROFILE)
    assert "1000" in summary
    assert "age" in summary
    assert "churn" in summary
    assert "customer_id" in summary


def test_sanitize_top_values_limits_to_five():
    top_values = [{"value": f"v{i}", "count": i} for i in range(20)]
    result = _sanitize_top_values(top_values)
    assert len(result) <= 5


def test_analyze_dataset_returns_expected_shape():
    mock_response = make_mock_response({
        "task_type": "classification",
        "task_type_confidence": 0.92,
        "task_type_reasoning": "churn is binary categorical",
        "target_candidates": [{"column": "churn", "reason": "binary categorical target"}],
        "data_quality_issues": [],
        "dataset_summary": "Telecom churn dataset with 1000 rows.",
    })
    with patch("app.services.ai_service._openai_chat") as mock_chat:
        mock_chat.return_value = mock_response
        result = analyze_dataset(SAMPLE_PROFILE)
    assert result["task_type"] in ("classification", "regression", "clustering", "unknown")
    assert "target_candidates" in result
    assert "dataset_summary" in result
    assert isinstance(result["task_type_confidence"], float)


def test_suggest_cleaning_actions_returns_list():
    mock_response = make_mock_response({
        "actions": [
            {
                "action_type": "drop_column",
                "column": "customer_id",
                "reason": "High-cardinality identifier, not predictive.",
                "priority": "high",
                "destructive": False,
            },
            {
                "action_type": "fill_missing",
                "column": "monthly_charge",
                "method": "median",
                "reason": "20 missing values; median is robust to outliers.",
                "priority": "medium",
                "destructive": False,
            },
        ]
    })
    with patch("app.services.ai_service._openai_chat") as mock_chat:
        mock_chat.return_value = mock_response
        result = suggest_cleaning_actions(SAMPLE_PROFILE, "classification")
    assert isinstance(result, list)
    assert len(result) >= 1
    assert result[0]["action_type"] in (
        "drop_column", "fill_missing", "remove_duplicates",
        "encode_categorical", "scale_numeric", "clip_outliers",
        "convert_type", "filter_rows", "derive_feature",
    )


def test_recommend_models_returns_ranked_list():
    mock_response = make_mock_response({
        "recommended_models": [
            {
                "model": "xgboost",
                "reason": "Strong tabular baseline for mixed feature types.",
                "confidence": 0.88,
                "warnings": [],
            },
            {
                "model": "logistic_regression",
                "reason": "Interpretable baseline; good for binary classification.",
                "confidence": 0.75,
                "warnings": ["May underfit if features have non-linear relationships."],
            },
        ],
        "baseline_model": "xgboost",
    })
    with patch("app.services.ai_service._openai_chat") as mock_chat:
        mock_chat.return_value = mock_response
        result = recommend_models(SAMPLE_PROFILE, "classification", "churn")
    assert isinstance(result["recommended_models"], list)
    assert len(result["recommended_models"]) >= 1
    assert "baseline_model" in result


def test_analyze_dataset_handles_openai_error():
    with patch("app.services.ai_service._openai_chat") as mock_chat:
        mock_chat.side_effect = Exception("API timeout")
        with pytest.raises(Exception, match="API timeout"):
            analyze_dataset(SAMPLE_PROFILE)


def test_translate_cleaning_command_returns_action_plan():
    mock_response = make_mock_response({
        "action_type": "filter_rows",
        "parameters": {"column": "age", "operator": "lt", "value": 18},
        "title": "Remove underage rows",
        "description": "Drops all rows where age is less than 18.",
        "confidence": 0.95,
        "warnings": [],
    })
    schema = [
        {"column_name": "age", "data_type": "numeric"},
        {"column_name": "salary", "data_type": "numeric"},
    ]
    with patch("app.services.ai_service._openai_chat") as mock_chat:
        mock_chat.return_value = mock_response
        from app.services.ai_service import translate_cleaning_command
        result = translate_cleaning_command("remove rows where age is less than 18", schema)
    assert result["action_type"] == "filter_rows"
    assert result["parameters"]["operator"] == "lt"
    assert isinstance(result["confidence"], float)
    assert isinstance(result["warnings"], list)


def test_translate_cleaning_command_handles_error():
    schema = [{"column_name": "age", "data_type": "numeric"}]
    with patch("app.services.ai_service._openai_chat") as mock_chat:
        mock_chat.side_effect = Exception("OpenAI timeout")
        from app.services.ai_service import translate_cleaning_command
        with pytest.raises(Exception, match="OpenAI timeout"):
            translate_cleaning_command("drop age column", schema)
