import { apiClient, ApiResponse } from "./client";

export interface AIInsight {
  id: string;
  dataset_id: string;
  dataset_version_id: string | null;
  insight_type:
    | "task_detection"
    | "cleaning_suggestion"
    | "model_recommendation"
    | "data_quality_warning";
  content: string | null;
  confidence_score: number | null;
  metadata_json: Record<string, unknown> | null;
  created_at: string;
}

export interface TranslateTrainingResult {
  task_type: string;
  model_type: string;
  target_column: string;
  confidence: number;
}

export const aiApi = {
  triggerAnalysis: (datasetId: string, datasetVersionId?: string) =>
    apiClient.post<ApiResponse<{ job_id: string }>>("/ai/analyze", {
      dataset_id: datasetId,
      dataset_version_id: datasetVersionId ?? null,
    }),

  getInsights: (datasetId: string) =>
    apiClient.get<ApiResponse<AIInsight[]>>(`/ai/insights/${datasetId}`),

  translateTrainingCommand: (body: { dataset_id: string; command: string }) =>
    apiClient.post<ApiResponse<TranslateTrainingResult>>("/ai/translate-training-command", body),

  recommendPipeline: (body: { dataset_id: string; project_id: string }) =>
    apiClient.post<ApiResponse<{ pipeline_id: string; pipeline_name: string }>>(
      "/ai/recommend-pipeline",
      body
    ),
};
