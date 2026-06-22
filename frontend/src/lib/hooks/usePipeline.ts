"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { pipelinesApi, SaveEdgeIn, SaveNodeIn } from "../api/pipelines";
import type { PipelineRunSummary } from "../api/pipelines";

export function usePipelineList(projectId: string) {
  return useQuery({
    queryKey: ["pipelines", projectId],
    queryFn: async () => (await pipelinesApi.list(projectId)).data.data,
    enabled: !!projectId,
  });
}

export function usePipeline(pipelineId: string) {
  return useQuery({
    queryKey: ["pipeline", pipelineId],
    queryFn: async () => (await pipelinesApi.get(pipelineId)).data.data,
    enabled: !!pipelineId,
  });
}

export function useCreatePipeline(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ name, datasetId }: { name: string; datasetId?: string }) =>
      (await pipelinesApi.create(projectId, name, datasetId)).data.data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["pipelines", projectId] });
    },
  });
}

export function useSavePipeline(pipelineId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      nodes,
      edges,
    }: {
      nodes: SaveNodeIn[];
      edges: SaveEdgeIn[];
    }) => (await pipelinesApi.save(pipelineId, nodes, edges)).data.data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["pipeline", pipelineId] });
    },
  });
}

export function useValidatePipeline(pipelineId: string) {
  return useMutation({
    mutationFn: async () => (await pipelinesApi.validate(pipelineId)).data.data,
  });
}

export function useExecutePipeline(pipelineId: string) {
  return useMutation({
    mutationFn: async () => (await pipelinesApi.execute(pipelineId)).data.data,
  });
}

export function useDeletePipeline(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (pipelineId: string) =>
      pipelinesApi.delete(pipelineId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["pipelines", projectId] });
    },
  });
}

export function usePipelineRuns(pipelineId: string) {
  return useQuery({
    queryKey: ["pipeline-runs", pipelineId],
    queryFn: async () => (await pipelinesApi.listRuns(pipelineId)).data.data,
    enabled: !!pipelineId,
    refetchInterval: (query) => {
      const runs = query.state.data as PipelineRunSummary[] | undefined;
      if (!runs) return 5000;
      const hasActive = runs.some(r => r.status === "queued" || r.status === "running");
      return hasActive ? 3000 : false;
    },
  });
}

export function useStartPipelineRun(pipelineId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => (await pipelinesApi.startRun(pipelineId)).data.data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["pipeline-runs", pipelineId] }),
  });
}
