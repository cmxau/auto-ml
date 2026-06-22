import { apiClient, ApiResponse } from "./client";

export interface Job {
  id: string;
  project_id: string;
  dataset_id: string | null;
  job_type: string;
  status: "queued" | "running" | "succeeded" | "failed";
  progress_percent: number | null;
  error_message: string | null;
  output_json: Record<string, unknown> | null;
  created_at: string;
}

export const jobsApi = {
  get: (id: string) => apiClient.get<ApiResponse<Job>>(`/jobs/${id}`),
  list: () => apiClient.get<ApiResponse<Job[]>>("/jobs"),
};
