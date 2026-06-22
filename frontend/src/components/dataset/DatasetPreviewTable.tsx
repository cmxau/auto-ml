"use client";

import { useDatasetVersionPreview } from "@/lib/hooks/useDatasets";
import { useState } from "react";

export function DatasetPreviewTable({ datasetId, versionId }: { datasetId: string; versionId: string | null }) {
  const [page, setPage] = useState(1);
  const { data, isLoading, isError } = useDatasetVersionPreview(datasetId, versionId, page);

  if (isLoading) {
    return <div className="h-40 bg-gray-100 rounded-xl animate-pulse" />;
  }

  if (isError) {
    return <p className="text-sm text-red-500">Failed to load preview.</p>;
  }

  if (!data || data.columns.length === 0) {
    return <p className="text-sm text-gray-500">No preview available.</p>;
  }

  const totalPages = Math.ceil(data.total_rows / 50);

  return (
    <div>
      <div className="overflow-auto rounded-xl border border-gray-200">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              {data.columns.map((col) => (
                <th
                  key={col}
                  className="px-4 py-2 text-left text-xs font-medium text-gray-500 whitespace-nowrap"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-100">
            {data.rows.map((row, i) => (
              <tr key={i} className="hover:bg-gray-50">
                {row.map((cell, j) => (
                  <td
                    key={j}
                    className="px-4 py-2 text-gray-700 whitespace-nowrap max-w-xs truncate"
                  >
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex items-center justify-between mt-3 text-sm text-gray-500">
        <span>{data.total_rows.toLocaleString()} total rows</span>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-1 rounded border border-gray-200 disabled:opacity-40 hover:bg-gray-50"
          >
            Prev
          </button>
          <span>
            Page {page} / {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            className="px-3 py-1 rounded border border-gray-200 disabled:opacity-40 hover:bg-gray-50"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
