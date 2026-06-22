import { apiClient, ApiResponse } from "./client";

export interface Project {
  id: string;
  name: string;
  description: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export const projectsApi = {
  create: (body: { name: string; description?: string }) =>
    apiClient.post<ApiResponse<Project>>("/projects", body),
  list: () => apiClient.get<ApiResponse<Project[]>>("/projects"),
  get: (id: string) => apiClient.get<ApiResponse<Project>>(`/projects/${id}`),
  update: (id: string, body: { name?: string; description?: string }) =>
    apiClient.patch<ApiResponse<Project>>(`/projects/${id}`, body),
  delete: (id: string) => apiClient.delete(`/projects/${id}`),
};
