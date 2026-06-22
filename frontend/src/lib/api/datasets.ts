import { apiClient, ApiResponse } from "./client";

export interface Dataset {
  id: string;
  name: string;
  source_type: string;
  original_file_name: string;
  file_format: string;
  row_count: number | null;
  column_count: number | null;
  status: string;
  created_at: string;
}

export interface ColumnProfile {
  column_name: string;
  data_type: string;
  missing_count: number;
  unique_count: number;
  mean_value: number | null;
  std_value: number | null;
  min_value: number | null;
  max_value: number | null;
  top_values: { value: string; count: number }[];
  example_values: string[];
  high_cardinality_flag: boolean;
}

export interface DatasetProfile {
  row_count: number;
  column_count: number;
  missing_value_count: number;
  duplicate_row_count: number;
  numeric_column_count: number;
  categorical_column_count: number;
  column_profiles: ColumnProfile[];
}

export interface DatasetVersionProfile {
  version_number: number;
  row_count: number | null;
  column_count: number | null;
  missing_value_count: number;
  duplicate_row_count: number;
  numeric_column_count: number;
  categorical_column_count: number;
  column_profiles: Omit<ColumnProfile, "top_values" | "example_values" | "high_cardinality_flag">[];
}

export interface PreviewData {
  columns: string[];
  rows: string[][];
  total_rows: number;
  page: number;
  page_size: number;
}

export const datasetsApi = {
  upload: (projectId: string, file: File) => {
    const form = new FormData();
    form.append("project_id", projectId);
    form.append("file", file);
    return apiClient.post<ApiResponse<{ dataset_id: string; job_id: string }>>(
      "/datasets/upload",
      form,
      { headers: { "Content-Type": "multipart/form-data" } }
    );
  },
  list: (projectId: string) =>
    apiClient.get<ApiResponse<Dataset[]>>(`/projects/${projectId}/datasets`),
  get: (id: string) => apiClient.get<ApiResponse<Dataset>>(`/datasets/${id}`),
  profile: (id: string) =>
    apiClient.get<ApiResponse<DatasetProfile | null>>(`/datasets/${id}/profile`),
  preview: (id: string, page = 1, pageSize = 50) =>
    apiClient.get<ApiResponse<PreviewData>>(
      `/datasets/${id}/preview?page=${page}&page_size=${pageSize}`
    ),
  previewVersion: (datasetId: string, versionId: string, page = 1, pageSize = 50) =>
    apiClient.get<ApiResponse<PreviewData>>(
      `/datasets/${datasetId}/versions/${versionId}/preview?page=${page}&page_size=${pageSize}`
    ),
  versions: (datasetId: string) =>
    apiClient.get<
      ApiResponse<
        { id: string; version_number: number; row_count: number | null; created_at: string }[]
      >
    >(`/datasets/${datasetId}/versions`),
  profileVersion: (datasetId: string, versionId: string) =>
    apiClient.get<ApiResponse<DatasetVersionProfile | null>>(
      `/datasets/${datasetId}/versions/${versionId}/profile`
    ),
  replace: (datasetId: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return apiClient.post<ApiResponse<{ dataset_id: string; version_id: string; job_id: string }>>(
      `/datasets/${datasetId}/replace`,
      form,
      { headers: { "Content-Type": "multipart/form-data" } }
    );
  },
  delete: (id: string) => apiClient.delete(`/datasets/${id}`),
  deleteVersion: (datasetId: string, versionId: string) =>
    apiClient.delete(`/datasets/${datasetId}/versions/${versionId}`),
};
