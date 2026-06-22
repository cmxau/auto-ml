"use client";
import { useEffect, useRef } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { datasetsApi } from "../api/datasets";

export function useDatasets(projectId: string) {
  return useQuery({
    queryKey: ["datasets", projectId],
    queryFn: async () => (await datasetsApi.list(projectId)).data.data,
    enabled: !!projectId,
  });
}

export function useDataset(id: string) {
  return useQuery({
    queryKey: ["dataset", id],
    queryFn: async () => (await datasetsApi.get(id)).data.data,
    enabled: !!id,
  });
}

export function useDatasetProfile(id: string) {
  return useQuery({
    queryKey: ["dataset-profile", id],
    queryFn: async () => (await datasetsApi.profile(id)).data.data,
    enabled: !!id,
    refetchInterval: (query) => {
      if (query.state.data) return false;
      if (query.state.error) return false;
      return 3000;
    },
  });
}

export function useDatasetPreview(id: string, page = 1) {
  return useQuery({
    queryKey: ["dataset-preview", id, page],
    queryFn: async () => (await datasetsApi.preview(id, page)).data.data,
    enabled: !!id,
  });
}

export function useDatasetVersionPreview(datasetId: string, versionId: string | null, page = 1) {
  return useQuery({
    queryKey: ["dataset-version-preview", datasetId, versionId, page],
    queryFn: async () => (await datasetsApi.previewVersion(datasetId, versionId!, page)).data.data,
    enabled: !!datasetId && !!versionId,
  });
}

export function useUploadDataset(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (file: File) =>
      (await datasetsApi.upload(projectId, file)).data.data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["datasets", projectId] }),
  });
}

export function useDatasetVersionProfile(datasetId: string, versionId: string | null) {
  return useQuery({
    queryKey: ["dataset-version-profile", datasetId, versionId],
    queryFn: async () => (await datasetsApi.profileVersion(datasetId, versionId!)).data.data,
    enabled: !!datasetId && !!versionId,
  });
}

export function useDatasetVersions(datasetId: string) {
  return useQuery({
    queryKey: ["dataset-versions", datasetId],
    queryFn: async () => (await datasetsApi.versions(datasetId)).data.data,
    enabled: !!datasetId,
  });
}

export function useDeleteDatasetVersion(datasetId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (versionId: string) => datasetsApi.deleteVersion(datasetId, versionId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["dataset-versions", datasetId] }),
  });
}

export function useDeleteDataset(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => datasetsApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["datasets", projectId] }),
  });
}

export function useReplaceDataset(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ datasetId, file }: { datasetId: string; file: File }) =>
      (await datasetsApi.replace(datasetId, file)).data.data,
    onSuccess: (_, { datasetId }) => {
      qc.invalidateQueries({ queryKey: ["datasets", projectId] });
      qc.invalidateQueries({ queryKey: ["dataset-versions", datasetId] });
      qc.invalidateQueries({ queryKey: ["dataset", datasetId] });
    },
  });
}

export function useWaitForNewVersion(
  datasetId: string,
  baselineCount: number | null,
  onReady: () => void,
) {
  const onReadyRef = useRef(onReady);
  onReadyRef.current = onReady;
  const qc = useQueryClient();

  const { data } = useQuery({
    queryKey: ["dataset-versions-poll", datasetId],
    queryFn: async () => (await datasetsApi.versions(datasetId)).data.data,
    enabled: baselineCount !== null && !!datasetId,
    refetchInterval: baselineCount !== null ? 2000 : false,
  });

  useEffect(() => {
    if (baselineCount !== null && data && data.length > baselineCount) {
      qc.invalidateQueries({ queryKey: ["dataset-versions", datasetId] });
      onReadyRef.current();
    }
  }, [data, baselineCount, datasetId, qc]);
}
