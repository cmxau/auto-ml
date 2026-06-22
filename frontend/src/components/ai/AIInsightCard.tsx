"use client";
import type { AIInsight } from "@/lib/api/ai";
import { ConfidenceBadge } from "./ConfidenceBadge";

const TYPE_LABELS: Record<string, string> = {
  task_detection: "Task Detection",
  cleaning_suggestion: "Cleaning Suggestions",
  model_recommendation: "Model Recommendations",
  data_quality_warning: "Data Quality",
};

const TYPE_COLORS: Record<string, string> = {
  task_detection: "border-blue-200 bg-blue-50",
  cleaning_suggestion: "border-orange-200 bg-orange-50",
  model_recommendation: "border-purple-200 bg-purple-50",
  data_quality_warning: "border-red-200 bg-red-50",
};

function TaskDetectionBody({
  meta,
}: {
  meta: Record<string, unknown>;
}) {
  const task = meta.task_type as string;
  const candidates = (
    meta.target_candidates as { column: string; reason: string }[]
  ) ?? [];
  const issues = (
    meta.data_quality_issues as {
      issue: string;
      severity: string;
    }[]
  ) ?? [];

  return (
    <div className="space-y-2 text-sm">
      <p>
        <span className="font-medium">Task type: </span>
        <span className="capitalize">{task}</span>
      </p>
      {candidates.length > 0 && (
        <div>
          <p className="font-medium mb-1">Target candidates:</p>
          <ul className="list-disc list-inside text-gray-600 ml-1 space-y-0.5">
            {candidates.map((c) => (
              <li key={c.column}>
                <code className="text-xs bg-gray-100 px-1 rounded">
                  {c.column}
                </code>{" "}
                — {c.reason}
              </li>
            ))}
          </ul>
        </div>
      )}
      {issues.length > 0 && (
        <div>
          <p className="font-medium mb-1">Quality issues:</p>
          <ul className="list-disc list-inside text-gray-600 ml-1 space-y-0.5">
            {issues.map((i, idx) => (
              <li key={idx}>
                <span
                  className={`text-xs font-medium mr-1 ${
                    i.severity === "high"
                      ? "text-red-600"
                      : i.severity === "medium"
                      ? "text-yellow-600"
                      : "text-gray-500"
                  }`}
                >
                  [{i.severity}]
                </span>
                {i.issue}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function CleaningBody({ meta }: { meta: Record<string, unknown> }) {
  const actions = (
    meta.actions as {
      action_type: string;
      column?: string;
      reason: string;
      priority: string;
    }[]
  ) ?? [];

  return (
    <div className="space-y-2">
      {actions.slice(0, 5).map((a, idx) => (
        <div
          key={idx}
          className="text-sm border border-gray-200 rounded-lg p-2 bg-white"
        >
          <div className="flex items-center gap-2 mb-1">
            <code className="text-xs bg-gray-100 px-1.5 py-0.5 rounded">
              {a.action_type}
            </code>
            {a.column && (
              <code className="text-xs text-blue-600">{a.column}</code>
            )}
            <span
              className={`text-xs ml-auto ${
                a.priority === "high"
                  ? "text-red-500"
                  : a.priority === "medium"
                  ? "text-yellow-500"
                  : "text-gray-400"
              }`}
            >
              {a.priority}
            </span>
          </div>
          <p className="text-gray-600 text-xs">{a.reason}</p>
        </div>
      ))}
      {actions.length > 5 && (
        <p className="text-xs text-gray-400">
          +{actions.length - 5} more suggestions
        </p>
      )}
    </div>
  );
}

function ModelRecommendationBody({
  meta,
}: {
  meta: Record<string, unknown>;
}) {
  const models = (
    meta.recommended_models as {
      model: string;
      reason: string;
      confidence: number;
      warnings: string[];
    }[]
  ) ?? [];
  const baseline = meta.baseline_model as string;

  return (
    <div className="space-y-2">
      {models.map((m, idx) => (
        <div
          key={idx}
          className="text-sm border border-gray-200 rounded-lg p-2 bg-white"
        >
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <code className="text-xs bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded">
              {m.model}
            </code>
            {m.model === baseline && (
              <span className="text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded">
                recommended
              </span>
            )}
            <ConfidenceBadge score={m.confidence} />
          </div>
          <p className="text-gray-600 text-xs">{m.reason}</p>
          {m.warnings?.length > 0 && (
            <p className="text-yellow-600 text-xs mt-1">
              ⚠ {m.warnings[0]}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}

export function AIInsightCard({ insight }: { insight: AIInsight }) {
  const meta = (insight.metadata_json ?? {}) as Record<string, unknown>;
  const colorClass =
    TYPE_COLORS[insight.insight_type] ?? "border-gray-200 bg-gray-50";

  return (
    <div className={`border rounded-xl p-4 ${colorClass}`}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-800">
          {TYPE_LABELS[insight.insight_type] ?? insight.insight_type}
        </h3>
        <ConfidenceBadge score={insight.confidence_score} />
      </div>
      {insight.content && (
        <p className="text-sm text-gray-700 mb-3">{insight.content}</p>
      )}
      {insight.insight_type === "task_detection" && (
        <TaskDetectionBody meta={meta} />
      )}
      {insight.insight_type === "cleaning_suggestion" && (
        <CleaningBody meta={meta} />
      )}
      {insight.insight_type === "model_recommendation" && (
        <ModelRecommendationBody meta={meta} />
      )}
    </div>
  );
}
