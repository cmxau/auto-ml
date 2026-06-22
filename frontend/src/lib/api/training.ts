import { apiClient, ApiResponse } from "./client";

export interface TrainingMetricRecord {
  id: string;
  training_run_id: string;
  metric_name: string;
  metric_value: number;
  metric_group: string;
}

export interface FeatureImportanceItem {
  feature: string;
  importance: number;
}

export interface ConfusionMatrixData {
  matrix: number[][];
  classes: string[];
}

export interface RocCurveData {
  fpr: number[];
  tpr: number[];
  auc: number;
}

export interface TrainingOutputJson {
  confusion_matrix?: ConfusionMatrixData;
  roc_curve?: RocCurveData;
}

export interface TrainingRunRecord {
  id: string;
  project_id: string;
  dataset_version_id: string;
  model_type: string;
  task_type: string;
  hyperparameters_json: Record<string, unknown> | null;
  train_status: "queued" | "running" | "succeeded" | "failed";
  start_time: string | null;
  end_time: string | null;
  selected_target_column: string;
  artifact_id: string | null;
  feature_importance_json: FeatureImportanceItem[] | null;
  output_json: TrainingOutputJson | null;
  error_message: string | null;
  created_at: string;
  metrics: TrainingMetricRecord[];
}

export interface TrainingSummary {
  summary: string;
  assessment: "excellent" | "good" | "fair" | "poor";
  suggestions: string[];
}

export interface ComparisonEntry {
  run_id: string;
  model_type: string;
  task_type: string;
  target_column: string;
  train_status: string;
  metrics: Record<string, number>;
}

export interface ModelDownloadResponse {
  url: string;
  file_name: string;
  expires_in: number;
}

export interface StartTrainingRequest {
  dataset_version_id: string;
  model_type: string;
  target_column: string;
  task_type: "classification" | "regression";
  hyperparameters?: Record<string, number | string>;
}

export const trainingApi = {
  start: (body: StartTrainingRequest) =>
    apiClient.post<ApiResponse<{ training_run_id: string; job_id: string }>>(
      "/training/start",
      body
    ),

  listForProject: (projectId: string) =>
    apiClient.get<ApiResponse<TrainingRunRecord[]>>(
      `/projects/${projectId}/training/runs`
    ),

  get: (runId: string) =>
    apiClient.get<ApiResponse<TrainingRunRecord>>(`/training/runs/${runId}`),

  getMetrics: (runId: string) =>
    apiClient.get<ApiResponse<TrainingMetricRecord[]>>(
      `/training/runs/${runId}/metrics`
    ),

  getFeatureImportance: (runId: string) =>
    apiClient.get<ApiResponse<FeatureImportanceItem[]>>(
      `/training/runs/${runId}/feature-importance`
    ),

  getSummary: (runId: string) =>
    apiClient.get<ApiResponse<TrainingSummary>>(
      `/training/runs/${runId}/summary`
    ),

  compare: (runIds: string[]) =>
    apiClient.post<ApiResponse<ComparisonEntry[]>>("/training/compare", {
      run_ids: runIds,
    }),

  download: (runId: string) =>
    apiClient.get(`/training/runs/${runId}/download`, { responseType: "blob" }),
};

export const MODEL_TYPE_LABELS: Record<string, string> = {
  logistic_regression: "Logistic Regression",
  random_forest: "Random Forest",
  xgboost: "XGBoost",
  linear_regression: "Linear Regression",
  random_forest_regressor: "Random Forest (Regression)",
  xgboost_regressor: "XGBoost (Regression)",
};

export const CLASSIFICATION_MODELS = [
  "logistic_regression",
  "random_forest",
  "xgboost",
] as const;

export const REGRESSION_MODELS = [
  "linear_regression",
  "random_forest_regressor",
  "xgboost_regressor",
] as const;
