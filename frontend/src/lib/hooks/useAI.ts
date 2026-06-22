"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { aiApi } from "../api/ai";
import type { TranslateTrainingResult } from "../api/ai";

export function useDatasetInsights(datasetId: string) {
  return useQuery({
    queryKey: ["ai-insights", datasetId],
    queryFn: async () => (await aiApi.getInsights(datasetId)).data.data,
    enabled: !!datasetId,
    refetchInterval: (query) => {
      const data = query.state.data;
      // fast poll when no insights yet; slow poll when insights exist (catches re-analysis after cleaning)
      if (!data || data.length === 0) return 4000;
      return 12000;
    },
  });
}

export function useTriggerAnalysis(datasetId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () =>
      (await aiApi.triggerAnalysis(datasetId)).data.data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ai-insights", datasetId] });
    },
  });
}

export function useTranslateTrainingCommand() {
  return useMutation<TranslateTrainingResult, Error, { dataset_id: string; command: string }>({
    mutationFn: async (body) =>
      (await aiApi.translateTrainingCommand(body)).data.data,
  });
}
