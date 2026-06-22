"use client";
import { useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { AppShell } from "@/components/layout/AppShell";
import { MetricsCard } from "@/components/training/MetricsCard";
import { FeatureImportanceChart } from "@/components/training/FeatureImportanceChart";
import { ConfusionMatrix } from "@/components/training/ConfusionMatrix";
import { RocCurve } from "@/components/training/RocCurve";
import { ErrorBanner } from "@/components/shared/ErrorBanner";
import { useTrainingRun, useTrainingSummary } from "@/lib/hooks/useTraining";
import { MODEL_TYPE_LABELS, trainingApi } from "@/lib/api/training";

const STATUS_COLORS: Record<string, string> = {
  succeeded: "bg-green-100 text-green-700",
  running: "bg-blue-100 text-blue-700",
  queued: "bg-yellow-100 text-yellow-700",
  failed: "bg-red-100 text-red-700",
};

const ASSESSMENT_COLORS: Record<string, string> = {
  excellent: "text-green-600",
  good: "text-blue-600",
  fair: "text-yellow-600",
  poor: "text-red-500",
};

export default function TrainingRunPage() {
  const { projectId, runId } = useParams<{
    projectId: string;
    runId: string;
  }>();
  const { data: run, isLoading } = useTrainingRun(runId);
  const {
    data: summary,
    refetch: fetchSummary,
    isFetching: loadingSummary,
  } = useTrainingSummary(runId);
  const [summaryRequested, setSummaryRequested] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  const navItems = [{ label: "Overview", href: `/projects/${projectId}` }];

  const handleGetSummary = async () => {
    setSummaryRequested(true);
    await fetchSummary();
  };

  const handleDownload = async () => {
    setDownloading(true);
    setDownloadError(null);
    try {
      const res = await trainingApi.download(runId);
      const blob = res.data as Blob;
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "model.joblib";
      a.click();
      URL.revokeObjectURL(url);
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setDownloadError(detail ?? "Download failed. Please try again.");
    } finally {
      setDownloading(false);
    }
  };

  return (
    <AppShell sideNavItems={navItems}>
      <div className="max-w-4xl mx-auto p-6 space-y-6">
        <div>
          <Link
            href={`/projects/${projectId}/training`}
            className="text-xs text-gray-400 hover:text-gray-600 mb-1 block"
          >
            ← Training runs
          </Link>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-semibold text-gray-900">
                {run
                  ? MODEL_TYPE_LABELS[run.model_type] ?? run.model_type
                  : "Loading…"}
              </h1>
              {run?.train_status && (
                <span
                  className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                    STATUS_COLORS[run.train_status] ?? "bg-gray-100 text-gray-600"
                  }`}
                >
                  {run.train_status}
                </span>
              )}
            </div>
            {run?.train_status === "succeeded" && (
              <div className="flex items-center gap-2">
                <button
                  onClick={handleDownload}
                  disabled={downloading}
                  className="text-sm px-4 py-2 bg-white border border-gray-200 text-gray-700 rounded-lg hover:bg-gray-50 disabled:opacity-50"
                >
                  {downloading ? "Preparing…" : "↓ Download model"}
                </button>
                {run.feature_importance_json && run.feature_importance_json.length > 0 && (
                  <button
                    onClick={() => {
                      const rows = [...run.feature_importance_json!]
                        .sort((a, b) => b.importance - a.importance)
                        .map((item) => `${item.feature},${item.importance}`);
                      const csv = ["feature,importance", ...rows].join("\n");
                      const blob = new Blob([csv], { type: "text/csv" });
                      const a = document.createElement("a");
                      a.href = URL.createObjectURL(blob);
                      a.download = "feature_importance.csv";
                      a.click();
                    }}
                    className="text-xs px-3 py-1.5 rounded-lg bg-gray-100 text-gray-700 hover:bg-gray-200"
                  >
                    ↓ Export feature importance
                  </button>
                )}
              </div>
            )}
          </div>
          {run && (
            <p className="text-sm text-gray-500 mt-1">
              {run.task_type} · target:{" "}
              <code className="bg-gray-100 px-1 rounded">
                {run.selected_target_column}
              </code>
            </p>
          )}
        </div>

        {downloadError && (
          <ErrorBanner message={downloadError} onDismiss={() => setDownloadError(null)} />
        )}

        {run && (run.train_status === "queued" || run.train_status === "running") && (
          <div className="flex items-center gap-2 text-sm text-blue-600 bg-blue-50 border border-blue-200 rounded-lg px-4 py-2">
            <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
            {run.train_status === "queued" ? "Waiting in queue…" : "Training in progress…"}
          </div>
        )}
        {run?.train_status === "failed" && (
          <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-2">
            Training failed: {run.error_message ?? "Unknown error"}
          </div>
        )}

        {isLoading || !run ? (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="h-32 bg-gray-100 rounded-xl animate-pulse"
              />
            ))}
          </div>
        ) : run.train_status === "succeeded" ? (
          <>
            <MetricsCard
              metrics={run.metrics}
              modelType={run.model_type}
              targetColumn={run.selected_target_column}
            />

            {run.feature_importance_json &&
              run.feature_importance_json.length > 0 && (
                <FeatureImportanceChart data={run.feature_importance_json} />
              )}

            {run.output_json?.confusion_matrix && (
              <ConfusionMatrix
                matrix={run.output_json.confusion_matrix.matrix}
                classes={run.output_json.confusion_matrix.classes}
              />
            )}

            {run.output_json?.roc_curve && (
              <RocCurve
                fpr={run.output_json.roc_curve.fpr}
                tpr={run.output_json.roc_curve.tpr}
                auc={run.output_json.roc_curve.auc}
              />
            )}

            <div className="bg-white border border-gray-200 rounded-xl p-6">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-gray-800">
                  AI Analysis
                </h3>
                {!summaryRequested && (
                  <button
                    onClick={handleGetSummary}
                    disabled={loadingSummary}
                    className="text-xs px-3 py-1.5 bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100 disabled:opacity-50"
                  >
                    {loadingSummary ? "Analysing…" : "Get AI summary"}
                  </button>
                )}
              </div>

              {summaryRequested && !summary && loadingSummary && (
                <div className="text-sm text-gray-400">
                  Generating summary…
                </div>
              )}

              {summary && (
                <div className="space-y-3">
                  <span
                    className={`text-xs font-semibold uppercase ${
                      ASSESSMENT_COLORS[summary.assessment] ?? "text-gray-600"
                    }`}
                  >
                    {summary.assessment}
                  </span>
                  <p className="text-sm text-gray-700">{summary.summary}</p>
                  {summary.suggestions.length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-gray-500 mb-1">
                        Suggestions:
                      </p>
                      <ul className="list-disc list-inside space-y-1">
                        {summary.suggestions.map((s, i) => (
                          <li key={i} className="text-sm text-gray-600">
                            {s}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          </>
        ) : null}
      </div>
    </AppShell>
  );
}
