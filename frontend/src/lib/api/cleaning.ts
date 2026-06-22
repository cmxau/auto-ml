import { apiClient, ApiResponse } from "./client";

export interface CleaningParameters {
  [key: string]: unknown;
}

export interface CleaningAction {
  action_type: string;
  parameters: CleaningParameters;
  title: string;
  description?: string;
  suggested_by?: "ai" | "user";
}

export interface PreviewResult {
  rows_before: number;
  rows_after: number;
  columns_before: number;
  columns_after: number;
  columns_added: string[];
  columns_removed: string[];
  sample_rows: Record<string, unknown>[];
}

export interface TranslatedAction {
  action_type: string | null;
  parameters: CleaningParameters;
  title: string;
  description: string;
  confidence: number;
  warnings: string[];
}

export interface CleaningActionRecord {
  id: string;
  dataset_version_id: string;
  action_type: string;
  title: string;
  description: string | null;
  parameters_json: CleaningParameters;
  status: "proposed" | "applied" | "failed";
  suggested_by: string;
  created_at: string;
}

export interface CleaningExecutionRecord {
  id: string;
  cleaning_action_id: string;
  input_version_id: string;
  output_version_id: string | null;
  execution_status: string;
  result_summary: string | null;
  error_message: string | null;
  executed_at: string | null;
  completed_at: string | null;
}

export interface CleaningHistoryItem {
  action: CleaningActionRecord;
  execution: CleaningExecutionRecord | null;
}

export const cleaningApi = {
  preview: (datasetVersionId: string, action: Omit<CleaningAction, "suggested_by">) =>
    apiClient.post<ApiResponse<PreviewResult>>("/cleaning/preview", {
      dataset_version_id: datasetVersionId,
      action_type: action.action_type,
      parameters: action.parameters,
    }),

  apply: (datasetVersionId: string, action: CleaningAction) =>
    apiClient.post<ApiResponse<{ job_id: string; cleaning_action_id: string }>>("/cleaning/apply", {
      dataset_version_id: datasetVersionId,
      action_type: action.action_type,
      parameters: action.parameters,
      title: action.title,
      description: action.description ?? null,
      suggested_by: action.suggested_by ?? "user",
    }),

  getHistory: (datasetId: string) =>
    apiClient.get<ApiResponse<CleaningHistoryItem[]>>(`/cleaning/history/${datasetId}`),

  translateCommand: (datasetId: string, command: string) =>
    apiClient.post<ApiResponse<TranslatedAction>>("/ai/translate-cleaning-command", {
      dataset_id: datasetId,
      command,
    }),
};
