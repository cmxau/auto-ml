"use client";

import { useDatasetProfile } from "@/lib/hooks/useDatasets";
import type { ColumnProfile } from "@/lib/api/datasets";

function StatCard({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 text-center">
      <p className="text-2xl font-semibold text-gray-900">{value ?? "—"}</p>
      <p className="text-xs text-gray-500 mt-1">{label}</p>
    </div>
  );
}

function ColumnCard({ col }: { col: ColumnProfile }) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4">
      <div className="flex items-start justify-between mb-2">
        <p className="font-medium text-gray-900 text-sm truncate">{col.column_name}</p>
        <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-600 ml-2 shrink-0">
          {col.data_type}
        </span>
      </div>
      {col.high_cardinality_flag && (
        <span className="text-xs text-amber-600 bg-amber-50 px-1.5 py-0.5 rounded">
          high cardinality
        </span>
      )}
      <p className="text-xs text-gray-400 mt-1">
        {col.unique_count?.toLocaleString()} unique
        {col.missing_count > 0 && (
          <span className="text-red-400"> · {col.missing_count} missing</span>
        )}
      </p>
      {col.data_type === "numeric" && col.mean_value != null && (
        <p className="text-xs text-gray-500 mt-1">
          mean: {col.mean_value.toFixed(2)} · range:{" "}
          {col.min_value?.toFixed(2)} – {col.max_value?.toFixed(2)}
        </p>
      )}
      {col.data_type === "categorical" && col.top_values.length > 0 && (
        <p className="text-xs text-gray-500 mt-1 line-clamp-2">
          Top:{" "}
          {col.top_values
            .slice(0, 3)
            .map((v) => `${v.value} (${v.count})`)
            .join(", ")}
        </p>
      )}
    </div>
  );
}

export function ProfileSummaryPanel({ datasetId }: { datasetId: string }) {
  const { data: profile, isLoading } = useDatasetProfile(datasetId);

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-24 bg-gray-100 rounded-xl animate-pulse" />
        ))}
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="text-center py-12 text-gray-500">
        <div className="w-6 h-6 border-2 border-blue-400 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
        <p className="text-sm">Profiling in progress…</p>
      </div>
    );
  }

  return (
    <div>
      <div className="grid grid-cols-3 gap-4 mb-6">
        <StatCard label="Rows" value={profile.row_count?.toLocaleString()} />
        <StatCard label="Columns" value={profile.column_count} />
        <StatCard label="Missing values" value={profile.missing_value_count?.toLocaleString()} />
        <StatCard label="Duplicate rows" value={profile.duplicate_row_count} />
        <StatCard label="Numeric cols" value={profile.numeric_column_count} />
        <StatCard label="Categorical cols" value={profile.categorical_column_count} />
      </div>

      <h3 className="text-sm font-medium text-gray-700 mb-3">Column profiles</h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {profile.column_profiles.map((col) => (
          <ColumnCard key={col.column_name} col={col} />
        ))}
      </div>
    </div>
  );
}
