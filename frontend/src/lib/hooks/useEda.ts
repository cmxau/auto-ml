"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { edaApi } from "../api/eda";

export function useEdaResults(datasetVersionId: string | null) {
  return useQuery({
    queryKey: ["eda-results", datasetVersionId],
    queryFn: async () =>
      (await edaApi.getResults(datasetVersionId!)).data.data,
    enabled: !!datasetVersionId,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data || data.status === "queued" || data.status === "running") {
        return 3000;
      }
      return false;
    },
  });
}

export function useTriggerEda(datasetId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (datasetVersionId?: string) =>
      (await edaApi.generate(datasetId, datasetVersionId)).data.data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["eda-results"] });
    },
  });
}
