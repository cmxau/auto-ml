import { apiClient, ApiResponse } from "./client";

export interface PipelineNodeRecord {
  id: string;
  pipeline_id: string;
  node_type: string;
  node_name: string;
  config_json: Record<string, unknown>;
  position_x: number | null;
  position_y: number | null;
}

export interface PipelineEdgeRecord {
  id: string;
  pipeline_id: string;
  source_node_id: string;
  target_node_id: string;
}

export interface PipelineRecord {
  id: string;
  project_id: string;
  dataset_id: string | null;
  name: string;
  description: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  nodes: PipelineNodeRecord[];
  edges: PipelineEdgeRecord[];
}

export interface SaveNodeIn {
  id?: string;
  node_type: string;
  node_name: string;
  config_json: Record<string, unknown>;
  position_x?: number;
  position_y?: number;
}

export interface SaveEdgeIn {
  source_node_id: string;
  target_node_id: string;
}

export interface ValidationResult {
  valid: boolean;
  errors: string[];
}

export interface PipelineRunSummary {
  id: string;
  status: string;
  current_node_id: string | null;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface PipelineRunDetail extends PipelineRunSummary {
  logs_json: Array<{ node_id?: string; type?: string; status: string; note?: string; training_run_id?: string }> | null;
  output_json: Record<string, unknown> | null;
}

export const pipelinesApi = {
  create: (projectId: string, name: string, datasetId?: string) =>
    apiClient.post<ApiResponse<PipelineRecord>>("/pipelines", {
      project_id: projectId,
      name,
      dataset_id: datasetId ?? null,
    }),

  list: (projectId: string) =>
    apiClient.get<ApiResponse<PipelineRecord[]>>(`/projects/${projectId}/pipelines`),

  get: (pipelineId: string) =>
    apiClient.get<ApiResponse<PipelineRecord>>(`/pipelines/${pipelineId}`),

  save: (pipelineId: string, nodes: SaveNodeIn[], edges: SaveEdgeIn[]) =>
    apiClient.patch<ApiResponse<PipelineRecord>>(`/pipelines/${pipelineId}`, {
      nodes,
      edges,
    }),

  validate: (pipelineId: string) =>
    apiClient.post<ApiResponse<ValidationResult>>(`/pipelines/${pipelineId}/validate`),

  execute: (pipelineId: string) =>
    apiClient.post<ApiResponse<{ job_id: string }>>(`/pipelines/${pipelineId}/execute`),

  delete: (pipelineId: string) =>
    apiClient.delete(`/pipelines/${pipelineId}`),

  startRun: (pipelineId: string) =>
    apiClient.post<ApiResponse<{ pipeline_run_id: string }>>(`/pipelines/${pipelineId}/run`),

  listRuns: (pipelineId: string) =>
    apiClient.get<ApiResponse<PipelineRunSummary[]>>(`/pipelines/${pipelineId}/runs`),

  getRun: (pipelineId: string, runId: string) =>
    apiClient.get<ApiResponse<PipelineRunDetail>>(`/pipelines/${pipelineId}/runs/${runId}`),
};
