"use client";

import { useUploadDataset } from "@/lib/hooks/useDatasets";
import { useJobPoller } from "@/lib/hooks/useJobPoller";
import { useRouter } from "next/navigation";
import { useCallback, useState } from "react";

export function DatasetUploadCard({ projectId }: { projectId: string }) {
  const upload = useUploadDataset(projectId);
  const router = useRouter();
  const [jobId, setJobId] = useState<string | null>(null);
  const [datasetId, setDatasetId] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);

  const job = useJobPoller(jobId);

  const handleFile = useCallback(
    async (file: File) => {
      try {
        const result = await upload.mutateAsync(file);
        setJobId(result.job_id);
        setDatasetId(result.dataset_id);
      } catch {
        // error shown via upload.isError
      }
    },
    [upload]
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  // Navigate when profiling completes
  if (job.data?.status === "succeeded" && datasetId && projectId) {
    router.push(`/projects/${projectId}/datasets/${datasetId}`);
  }

  const isBusy = upload.isPending || (!!jobId && job.data?.status !== "succeeded" && job.data?.status !== "failed");

  return (
    <div
      onDrop={onDrop}
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      className={`border-2 border-dashed rounded-xl p-10 text-center transition-colors ${
        dragOver ? "border-blue-400 bg-blue-50" : "border-gray-300 bg-white"
      }`}
    >
      {isBusy ? (
        <div className="space-y-3">
          <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-sm text-gray-600">
            {upload.isPending
              ? "Uploading…"
              : job.data?.status === "running"
              ? "Profiling dataset…"
              : "Queued for profiling…"}
          </p>
        </div>
      ) : (
        <>
          <p className="text-gray-600 mb-3">Drag &amp; drop a CSV or XLSX file here</p>
          <label className="cursor-pointer inline-block bg-blue-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-blue-700">
            Choose file
            <input
              type="file"
              accept=".csv,.xlsx,.json"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) handleFile(f);
                e.target.value = "";
              }}
            />
          </label>
          <p className="text-xs text-gray-400 mt-3">CSV, XLSX, or JSON · max 100 MB</p>
        </>
      )}
      {upload.isError && (
        <p className="text-red-500 text-sm mt-3">
          Upload failed. Check the file format and try again.
        </p>
      )}
      {job.data?.status === "failed" && (
        <p className="text-red-500 text-sm mt-3">
          Profiling failed: {job.data.error_message ?? "unknown error"}
        </p>
      )}
    </div>
  );
}
