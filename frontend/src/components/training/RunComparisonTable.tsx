"use client";
import type { ComparisonEntry } from "@/lib/api/training";
import { MODEL_TYPE_LABELS } from "@/lib/api/training";

interface Props {
  runs: ComparisonEntry[];
}

export function RunComparisonTable({ runs }: Props) {
  if (runs.length === 0) return null;

  const metricNames = Array.from(
    new Set(runs.flatMap((r) => Object.keys(r.metrics)))
  );

  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-auto">
      <table className="text-sm w-full">
        <thead className="bg-gray-50 border-b border-gray-200">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">
              Metric
            </th>
            {runs.map((r) => (
              <th
                key={r.run_id}
                className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase"
              >
                {MODEL_TYPE_LABELS[r.model_type] ?? r.model_type}
                <span className="block font-normal text-gray-400 normal-case mt-0.5">
                  → {r.target_column}
                </span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {metricNames.map((name, i) => (
            <tr key={name} className={i % 2 === 0 ? "bg-white" : "bg-gray-50"}>
              <td className="px-4 py-2 font-medium text-gray-700 capitalize">
                {name.replace(/_/g, " ")}
              </td>
              {runs.map((r) => {
                const val = r.metrics[name];
                return (
                  <td key={r.run_id} className="px-4 py-2 text-gray-600">
                    {val != null ? val.toFixed(4) : "—"}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
