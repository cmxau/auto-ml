"use client";
import { useCleaningHistory } from "@/lib/hooks/useCleaning";

interface Props { datasetId: string }

export function CleaningHistoryPanel({ datasetId }: Props) {
  const { data: history, isLoading } = useCleaningHistory(datasetId);

  if (isLoading) return <div className="h-32 bg-gray-100 rounded-xl animate-pulse" />;
  if (!history || history.length === 0) {
    return <p className="text-sm text-gray-400 py-8 text-center">No cleaning actions applied yet.</p>;
  }

  const applied = history.filter(h => h.action.status === "applied");
  const failed = history.filter(h => h.action.status === "failed");

  return (
    <div className="space-y-2">
      <p className="text-xs text-gray-500 mb-3">
        {applied.length} transformation{applied.length !== 1 ? "s" : ""} applied
        {failed.length > 0 && ` · ${failed.length} failed`}
      </p>
      {history.map((item, i) => (
        <div key={item.action.id}
          className={`border rounded-xl p-3 text-xs ${
            item.action.status === "applied"
              ? "border-green-200 bg-green-50"
              : item.action.status === "failed"
              ? "border-red-200 bg-red-50"
              : "border-gray-200 bg-white"
          }`}>
          <div className="flex items-center gap-2 mb-1">
            <span className={`font-medium ${
              item.action.status === "applied" ? "text-green-700"
              : item.action.status === "failed" ? "text-red-700"
              : "text-gray-600"
            }`}>
              {item.action.status === "applied" ? "✓" : item.action.status === "failed" ? "✗" : "○"}
            </span>
            <code className="bg-white border border-gray-200 px-1.5 py-0.5 rounded text-gray-700">
              {item.action.action_type}
            </code>
            {(item.action.parameters_json as Record<string,unknown>)?.column && (
              <code className="text-blue-600">
                {String((item.action.parameters_json as Record<string,unknown>).column)}
              </code>
            )}
            <span className="ml-auto text-gray-400">
              {new Date(item.action.created_at).toLocaleString()}
            </span>
          </div>
          <p className="text-gray-600 ml-5">{item.action.title}</p>
          {item.execution?.result_summary && (
            <p className="text-gray-500 ml-5 mt-1">{item.execution.result_summary}</p>
          )}
          {item.execution?.error_message && (
            <p className="text-red-600 ml-5 mt-1">{item.execution.error_message}</p>
          )}
        </div>
      ))}
    </div>
  );
}
