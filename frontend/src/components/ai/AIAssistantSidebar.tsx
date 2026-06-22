"use client";
import { useDatasetInsights, useTriggerAnalysis } from "@/lib/hooks/useAI";
import { AIInsightCard } from "./AIInsightCard";

interface Props {
  datasetId: string;
  datasetStatus: string;
}

export function AIAssistantSidebar({ datasetId, datasetStatus }: Props) {
  const { data: insights, isLoading } = useDatasetInsights(datasetId);
  const trigger = useTriggerAnalysis(datasetId);

  const isReady = datasetStatus === "ready";

  return (
    <aside className="w-80 border-l border-gray-200 bg-white h-full flex flex-col shrink-0 overflow-hidden">
      <div className="p-4 border-b border-gray-200 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-900">AI Analysis</h2>
        {isReady && (
          <button
            onClick={() => trigger.mutate()}
            disabled={trigger.isPending}
            className="text-xs bg-blue-50 text-blue-600 px-2 py-1 rounded hover:bg-blue-100 disabled:opacity-50"
          >
            {trigger.isPending ? "Running…" : "Re-analyze"}
          </button>
        )}
      </div>

      <div className="flex-1 overflow-auto p-4 space-y-4">
        {!isReady ? (
          <div className="text-center py-8 text-gray-400">
            <p className="text-sm">Dataset still processing…</p>
          </div>
        ) : isLoading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-24 bg-gray-100 rounded-xl animate-pulse" />
            ))}
          </div>
        ) : !insights || insights.length === 0 ? (
          <div className="text-center py-8 text-gray-400">
            <div className="w-5 h-5 border-2 border-blue-300 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
            <p className="text-sm">Analyzing dataset…</p>
          </div>
        ) : (
          insights.map((insight) => (
            <AIInsightCard key={insight.id} insight={insight} />
          ))
        )}
      </div>
    </aside>
  );
}
