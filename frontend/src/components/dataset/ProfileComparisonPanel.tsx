"use client";
import { useDatasetVersions, useDatasetVersionProfile } from "@/lib/hooks/useDatasets";
import type { DatasetVersionProfile } from "@/lib/api/datasets";

interface Props {
  datasetId: string;
  activeVersionId: string | null;
}

interface StatBlockProps {
  label: string;
  base: number | null;
  current: number | null;
  isSingleVersion: boolean;
}

function StatBlock({ label, base, current, isSingleVersion }: StatBlockProps) {
  const changed = !isSingleVersion && base !== null && current !== null && base !== current;
  const improved = changed && (current ?? 0) < (base ?? 0);
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-3">
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <div className="flex items-baseline gap-2">
        <span className="text-lg font-semibold text-gray-900">{current ?? base ?? "—"}</span>
        {changed && (
          <span className={`text-xs font-medium ${improved ? "text-green-600" : "text-red-500"}`}>
            {improved ? "↓" : "↑"} {Math.abs((current ?? 0) - (base ?? 0))} from v0
          </span>
        )}
      </div>
    </div>
  );
}

export function ProfileComparisonPanel({ datasetId, activeVersionId }: Props) {
  const { data: versions } = useDatasetVersions(datasetId);
  const baseVersionId = versions
    ? [...versions].sort((a, b) => a.version_number - b.version_number)[0]?.id
    : null;

  const { data: baseProfile, isLoading: baseLoading } = useDatasetVersionProfile(datasetId, baseVersionId ?? null);
  const { data: currentProfile, isLoading: currentLoading } = useDatasetVersionProfile(datasetId, activeVersionId);

  const isSingleVersion = baseVersionId === activeVersionId;

  if (baseLoading || currentLoading) {
    return <div className="h-32 bg-gray-100 rounded-xl animate-pulse" />;
  }

  if (!baseProfile) {
    return <p className="text-sm text-gray-400 py-8 text-center">Profile not yet computed.</p>;
  }

  return (
    <div className="space-y-4">
      {!isSingleVersion && (
        <div className="text-xs text-blue-600 bg-blue-50 border border-blue-200 rounded-lg px-3 py-2">
          Comparing v0 (original) → v{currentProfile?.version_number ?? "?"} (current)
        </div>
      )}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <StatBlock
          label="Rows"
          base={baseProfile.row_count}
          current={currentProfile?.row_count ?? null}
          isSingleVersion={isSingleVersion}
        />
        <StatBlock
          label="Columns"
          base={baseProfile.column_count}
          current={currentProfile?.column_count ?? null}
          isSingleVersion={isSingleVersion}
        />
        <StatBlock
          label="Missing values"
          base={baseProfile.missing_value_count}
          current={currentProfile?.missing_value_count ?? null}
          isSingleVersion={isSingleVersion}
        />
        <StatBlock
          label="Duplicate rows"
          base={baseProfile.duplicate_row_count}
          current={currentProfile?.duplicate_row_count ?? null}
          isSingleVersion={isSingleVersion}
        />
      </div>

      {/* Column-by-column comparison */}
      <div className="overflow-auto rounded-xl border border-gray-200">
        <table className="min-w-full text-xs">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="px-3 py-2 text-left text-gray-500">Column</th>
              <th className="px-3 py-2 text-left text-gray-500">Type</th>
              <th className="px-3 py-2 text-right text-gray-500">Missing (v0)</th>
              {!isSingleVersion && <th className="px-3 py-2 text-right text-gray-500">Missing (now)</th>}
              <th className="px-3 py-2 text-right text-gray-500">Unique</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-100">
            {(baseProfile.column_profiles ?? []).map((col) => {
              const curr = currentProfile?.column_profiles?.find(
                (c) => c.column_name === col.column_name
              );
              const missingChanged = !isSingleVersion && curr && curr.missing_count !== col.missing_count;
              return (
                <tr key={col.column_name} className="hover:bg-gray-50">
                  <td className="px-3 py-2 font-mono text-gray-800">{col.column_name}</td>
                  <td className="px-3 py-2 text-gray-500">{col.data_type}</td>
                  <td className="px-3 py-2 text-right text-gray-700">{col.missing_count ?? 0}</td>
                  {!isSingleVersion && (
                    <td
                      className={`px-3 py-2 text-right font-medium ${
                        missingChanged
                          ? (curr?.missing_count ?? 0) < (col.missing_count ?? 0)
                            ? "text-green-600"
                            : "text-red-500"
                          : "text-gray-700"
                      }`}
                    >
                      {curr?.missing_count ?? "—"}
                    </td>
                  )}
                  <td className="px-3 py-2 text-right text-gray-700">{col.unique_count ?? "—"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
