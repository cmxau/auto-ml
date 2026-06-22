import json
import logging
from typing import Any, Dict, List

from openai import OpenAI

logger = logging.getLogger(__name__)

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        from app.config import settings  # lazy import to avoid module-load validation errors in tests
        _client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


def _openai_chat(system: str, user: str) -> Any:
    """Single OpenAI call with JSON mode. Separated for easy mocking in tests."""
    from app.config import settings  # lazy import
    return _get_client().chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )


def _sanitize_top_values(top_values: list) -> list:
    """Keep at most 5 top values to limit prompt size."""
    return top_values[:5]


def _build_profile_summary(profile: dict) -> str:
    """Build a compact, prompt-safe summary of the dataset profile."""
    lines = [
        f"Rows: {profile['row_count']}",
        f"Columns: {profile['column_count']}",
        f"Total missing values: {profile['missing_value_count']}",
        f"Duplicate rows: {profile['duplicate_row_count']}",
        "",
        "Column details:",
    ]
    for col in profile.get("columns", []):
        line = f"  - {col['column_name']} ({col['data_type']})"
        line += f", missing={col['missing_count']}, unique={col['unique_count']}"
        if col["data_type"] == "numeric" and col.get("mean_value") is not None:
            line += f", mean={col['mean_value']:.2f}, range=[{col['min_value']:.2f}, {col['max_value']:.2f}]"
        if col["data_type"] == "categorical" and col.get("top_values"):
            safe_vals = _sanitize_top_values(col["top_values"])
            tops = ", ".join(f"{v['value']}({v['count']})" for v in safe_vals)
            line += f", top_values=[{tops}]"
        if col.get("high_cardinality_flag"):
            line += " [HIGH CARDINALITY]"
        lines.append(line)
    return "\n".join(lines)


def analyze_dataset(profile: dict) -> Dict[str, Any]:
    """Dataset Analyst Agent — infers task type, target candidates, data quality issues."""
    system = (
        "You are a data science assistant. Analyze the dataset profile and return a JSON object with these exact keys: "
        "task_type (one of: classification, regression, clustering, unknown), "
        "task_type_confidence (float 0.0-1.0), "
        "task_type_reasoning (string), "
        "target_candidates (array of {column, reason}), "
        "data_quality_issues (array of {issue, severity, columns}), "
        "dataset_summary (2-3 sentence plain language description). "
        "Never reference or quote raw data values. Base your analysis only on statistics and column names."
    )
    user = f"Dataset profile:\n\n{_build_profile_summary(profile)}"
    response = _openai_chat(system, user)
    return json.loads(response.choices[0].message.content)


def suggest_cleaning_actions(profile: dict, task_type: str) -> List[Dict[str, Any]]:
    """Cleaning Advisor Agent — returns ordered list of recommended cleaning actions."""
    system = (
        "You are a data cleaning advisor. Given a dataset profile and inferred ML task, "
        "return a JSON object with key 'actions' containing an ordered array of cleaning recommendations. "
        "Each action must have: action_type (one of: drop_column, fill_missing, remove_duplicates, "
        "encode_categorical, scale_numeric, clip_outliers, convert_type, filter_rows, derive_feature), "
        "column (string or null for row-level ops), reason (string), priority (high/medium/low), "
        "destructive (boolean). "
        "Order from highest to lowest priority. Include only actions that are clearly justified."
    )
    user = (
        f"Task type: {task_type}\n\n"
        f"Dataset profile:\n\n{_build_profile_summary(profile)}"
    )
    response = _openai_chat(system, user)
    parsed = json.loads(response.choices[0].message.content)
    return parsed.get("actions", [])


def recommend_models(profile: dict, task_type: str, target_column: str) -> Dict[str, Any]:
    """Model Recommendation Agent — ranks candidate model families."""
    system = (
        "You are an ML model selection advisor. Given a dataset profile, task type, and target column, "
        "return a JSON object with: "
        "recommended_models (array of {model, reason, confidence, warnings}), "
        "baseline_model (string — the single best starting point). "
        "Valid model values: logistic_regression, random_forest, xgboost, linear_regression, "
        "random_forest_regressor, xgboost_regressor, kmeans. "
        "Rank from most to least recommended. Keep reasons concise (one sentence each)."
    )
    user = (
        f"Task type: {task_type}\n"
        f"Target column: {target_column}\n\n"
        f"Dataset profile:\n\n{_build_profile_summary(profile)}"
    )
    response = _openai_chat(system, user)
    return json.loads(response.choices[0].message.content)


def translate_cleaning_command(command: str, schema: List[Dict[str, Any]]) -> Dict[str, Any]:
    """NL Command Agent — converts plain-language instruction to a structured action plan."""
    valid_action_types = (
        "drop_column, fill_missing, remove_duplicates, filter_rows, "
        "encode_categorical, scale_numeric, convert_type, clip_outliers, derive_feature"
    )
    schema_summary = "\n".join(
        f"  - {c['column_name']} ({c['data_type']})" for c in schema
    )
    system = (
        "You are a data cleaning command interpreter. "
        "Convert the user's natural-language cleaning instruction into a JSON action plan. "
        f"Valid action_type values: {valid_action_types}. "
        "Return a JSON object with these exact keys: "
        "action_type (string or null if ambiguous), parameters (object with action-specific keys), "
        "title (short human-readable description), description (1 sentence explaining what will change), "
        "confidence (float 0.0-1.0), warnings (array of strings, empty if none). "
        "\n\nParameter shapes per action_type:\n"
        '  drop_column: {"column": "<name>"}\n'
        '  fill_missing: {"column": "<name>", "method": "<mean|median|mode|constant>", "value": <only for constant>}\n'
        '  remove_duplicates: {"subset": null or ["col1", "col2"]}\n'
        '  filter_rows: {"column": "<name>", "operator": "<lt|gt|le|ge|eq|ne>", "value": <number or string>}\n'
        '  encode_categorical: {"column": "<name>", "method": "<onehot|label>"}\n'
        '  scale_numeric: {"column": "<name>", "method": "<standard|minmax>"}\n'
        '  convert_type: {"column": "<name>", "dtype": "<int|float|str|datetime>"}\n'
        '  clip_outliers: {"column": "<name>", "method": "<iqr|zscore>", "threshold": <optional float>}\n'
        '  derive_feature: {"new_column": "<name>", "left_column": "<name>", '
        '"operator": "<add|subtract|multiply|divide>", "right_column": "<name>" OR "right_value": <number>}\n'
        "\nIf the command is ambiguous or unsupported, set action_type to null and explain in warnings."
    )
    user = (
        f"Dataset columns:\n{schema_summary}\n\n"
        f"User command: {command}"
    )
    response = _openai_chat(system, user)
    return json.loads(response.choices[0].message.content)


def summarize_training_results(
    model_type: str,
    task_type: str,
    metrics: Dict[str, Any],
    feature_importance: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Experiment Review Agent — explains training results for beginners."""
    top_features = feature_importance[:5]
    system = (
        "You are an ML experiment reviewer helping a beginner understand their results. "
        "Return a JSON object with keys: "
        "summary (2-3 sentences describing what the model achieved and whether it is good), "
        "assessment (one of: excellent, good, fair, poor), "
        "suggestions (array of 2-3 short actionable improvement tips). "
        "Reference specific metric values. Be honest but encouraging."
    )
    user = (
        f"Model type: {model_type}\n"
        f"Task: {task_type}\n"
        f"Metrics: {metrics}\n"
        f"Top features by importance: {top_features}"
    )
    response = _openai_chat(system, user)
    return json.loads(response.choices[0].message.content)
