import { apiClient, ApiResponse } from "./client";

export type ChartType =
  | "missing_heatmap"
  | "histogram"
  | "bar_chart"
  | "correlation_matrix";

export interface MissingHeatmapItem {
  column: string;
  missing_count: number;
  missing_pct: number;
}

export interface HistogramData {
  bins: number[];
  counts: number[];
}

export interface BarChartData {
  labels: string[];
  counts: number[];
}

export interface CorrelationMatrixData {
  columns: string[];
  matrix: number[][];
}

export interface Chart {
  type: ChartType;
  column?: string;
  title: string;
  data:
    | MissingHeatmapItem[]
    | HistogramData
    | BarChartData
    | CorrelationMatrixData;
}

export interface EdaResult {
  id: string;
  dataset_version_id: string;
  status: string;
  charts_json: Chart[] | null;
  error_message: string | null;
  created_at: string;
}

export const edaApi = {
  generate: (datasetId: string, datasetVersionId?: string) =>
    apiClient.post<ApiResponse<{ job_id: string }>>("/eda/generate", {
      dataset_id: datasetId,
      dataset_version_id: datasetVersionId ?? null,
    }),

  getResults: (datasetVersionId: string) =>
    apiClient.get<ApiResponse<EdaResult | null>>(
      `/eda/${datasetVersionId}`
    ),
};
