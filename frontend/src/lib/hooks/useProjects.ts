"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { projectsApi } from "../api/projects";

export function useProjects() {
  return useQuery({
    queryKey: ["projects"],
    queryFn: async () => (await projectsApi.list()).data.data,
  });
}

export function useProject(id: string) {
  return useQuery({
    queryKey: ["projects", id],
    queryFn: async () => (await projectsApi.get(id)).data.data,
    enabled: !!id,
  });
}

export function useCreateProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { name: string; description?: string }) =>
      (await projectsApi.create(body)).data.data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["projects"] }),
  });
}

export function useDeleteProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => projectsApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["projects"] }),
  });
}

export function useUpdateProject(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { name?: string; description?: string }) =>
      (await projectsApi.update(projectId, body)).data.data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["projects", projectId] });
      qc.invalidateQueries({ queryKey: ["projects"] });
    },
  });
}
