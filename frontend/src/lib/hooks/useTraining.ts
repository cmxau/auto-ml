"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { trainingApi } from "../api/training";

export function useProjectTrainingRuns(projectId: string) {
  return useQuery({
    queryKey: ["training-runs", projectId],
    queryFn: async () => (await trainingApi.listForProject(projectId)).data.data,
    enabled: !!projectId,
  });
}

export function useTrainingRun(runId: string) {
  return useQuery({
    queryKey: ["training-run", runId],
    queryFn: async () => (await trainingApi.get(runId)).data.data,
    enabled: !!runId,
    refetchInterval: (query) => {
      const status = query.state.data?.train_status;
      if (status === "succeeded" || status === "failed") return false;
      return 3000;
    },
  });
}

export function useStartTraining(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: import("@/lib/api/training").StartTrainingRequest) => (await trainingApi.start(body)).data.data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["training-runs", projectId] });
    },
  });
}

export function useTrainingSummary(runId: string) {
  return useQuery({
    queryKey: ["training-summary", runId],
    queryFn: async () => (await trainingApi.getSummary(runId)).data.data,
    enabled: false,
  });
}

export function useCompareRuns() {
  return useMutation({
    mutationFn: async (runIds: string[]) =>
      (await trainingApi.compare(runIds)).data.data,
  });
}
