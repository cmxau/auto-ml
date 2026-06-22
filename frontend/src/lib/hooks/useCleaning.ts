"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { cleaningApi, CleaningAction } from "../api/cleaning";

export function useCleaningHistory(datasetId: string) {
  return useQuery({
    queryKey: ["cleaning-history", datasetId],
    queryFn: async () => (await cleaningApi.getHistory(datasetId)).data.data,
    enabled: !!datasetId,
  });
}

export function usePreviewAction(datasetVersionId: string | null) {
  return useMutation({
    mutationFn: async (action: Omit<CleaningAction, "suggested_by">) => {
      if (!datasetVersionId) throw new Error("No dataset version");
      return (await cleaningApi.preview(datasetVersionId, action)).data.data;
    },
  });
}

export function useApplyAction(datasetId: string, datasetVersionId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (action: CleaningAction) => {
      if (!datasetVersionId) throw new Error("No dataset version");
      return (await cleaningApi.apply(datasetVersionId, action)).data.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cleaning-history", datasetId] });
      qc.invalidateQueries({ queryKey: ["dataset-versions", datasetId] });
      qc.invalidateQueries({ queryKey: ["dataset", datasetId] });
      qc.invalidateQueries({ queryKey: ["ai-insights", datasetId] });
    },
  });
}

export function useTranslateCommand(datasetId: string) {
  return useMutation({
    mutationFn: async (command: string) =>
      (await cleaningApi.translateCommand(datasetId, command)).data.data,
  });
}
