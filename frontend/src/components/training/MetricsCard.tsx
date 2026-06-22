"use client";
import type { TrainingMetricRecord } from "@/lib/api/training";

const METRIC_LABELS: Record<string, string> = {
  accuracy: "Accuracy",
  f1_score: "F1 Score",
  precision: "Precision",
  recall: "Recall",
  roc_auc: "ROC AUC",
  r2_score: "R² Score",
  rmse: "RMSE",
  mae: "MAE",
  mse: "MSE",
};

function metricColor(name: string, value: number): string {
  const lowerIsBetter = ["rmse", "mae", "mse"];
  if (lowerIsBetter.includes(name)) {
    return value < 100 ? "text-green-600" : "text-yellow-600";
  }
  if (value >= 0.9) return "text-green-600";
  if (value >= 0.7) return "text-yellow-600";
  return "text-red-500";
}

interface Props {
  metrics: TrainingMetricRecord[];
  modelType: string;
  targetColumn: string;
}

export function MetricsCard({ metrics, modelType, targetColumn }: Props) {
  if (metrics.length === 0) {
    return (
      <div className="bg-white border border-gray-200 rounded-xl p-6">
        <p className="text-sm text-gray-400 text-center">No metrics available yet.</p>
      </div>
    );
  }

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-6">
      <div className="mb-4">
        <h3 className="text-sm font-semibold text-gray-800">Model Results</h3>
        <p className="text-xs text-gray-500 mt-0.5">
          {METRIC_LABELS[modelType] ?? modelType} · target:{" "}
          <code className="bg-gray-100 px-1 rounded">{targetColumn}</code>
        </p>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
        {metrics.map((m) => (
          <div key={m.metric_name} className="bg-gray-50 rounded-lg p-3">
            <p className="text-xs text-gray-500 mb-1">
              {METRIC_LABELS[m.metric_name] ?? m.metric_name}
            </p>
            <p className={`text-lg font-bold ${metricColor(m.metric_name, m.metric_value)}`}>
              {m.metric_value.toFixed(4)}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
