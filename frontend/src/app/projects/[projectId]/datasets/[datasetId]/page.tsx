"use client";

import { AppShell } from "@/components/layout/AppShell";
import { DatasetPreviewTable } from "@/components/dataset/DatasetPreviewTable";
import { ProfileSummaryPanel } from "@/components/dataset/ProfileSummaryPanel";
import { ProfileComparisonPanel } from "@/components/dataset/ProfileComparisonPanel";
import { AIAssistantSidebar } from "@/components/ai/AIAssistantSidebar";
import { MissingHeatmap } from "@/components/eda/MissingHeatmap";
import { DistributionChart } from "@/components/eda/DistributionChart";
import { CorrelationMatrix } from "@/components/eda/CorrelationMatrix";
import { useDataset, useDatasetVersions, useDatasetProfile, useDeleteDatasetVersion } from "@/lib/hooks/useDatasets";
import { useEdaResults } from "@/lib/hooks/useEda";
import type {
  MissingHeatmapItem,
  CorrelationMatrixData,
  Chart,
} from "@/lib/api/eda";
import { CleaningCommandBox } from "@/components/dataset/CleaningCommandBox";
import { CleaningSuggestionList } from "@/components/dataset/CleaningSuggestionList";
import { CleaningHistoryPanel } from "@/components/dataset/CleaningHistoryPanel";
import { useDatasetInsights, useTranslateTrainingCommand } from "@/lib/hooks/useAI";
import type { AIInsight } from "@/lib/api/ai";
import { useParams } from "next/navigation";
import { useState, useEffect } from "react";
import Link from "next/link";
import { useStartTraining } from "@/lib/hooks/useTraining";
import { MODEL_TYPE_LABELS, CLASSIFICATION_MODELS, REGRESSION_MODELS } from "@/lib/api/training";
import { HyperparameterForm, defaultHyperparams } from "@/components/training/HyperparameterForm";
import { ErrorBanner } from "@/components/shared/ErrorBanner";
import { ErrorBoundary } from "@/components/shared/ErrorBoundary";

type Tab = "profile" | "eda" | "clean" | "history" | "train" | "preview";

function EdaPanel({ datasetVersionId }: { datasetVersionId: string | null }) {
  const { data: edaResult, isLoading } = useEdaResults(datasetVersionId);

  if (!datasetVersionId || isLoading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-48 bg-gray-100 rounded-xl animate-pulse" />
        ))}
      </div>
    );
  }

  if (!edaResult || edaResult.status !== "succeeded" || !edaResult.charts_json) {
    const isProcessing =
      !edaResult ||
      edaResult.status === "queued" ||
      edaResult.status === "running";
    const msg = isProcessing
      ? "Computing EDA charts…"
      : edaResult?.status === "failed"
      ? `EDA failed: ${edaResult.error_message}`
      : "No EDA results yet.";

    return (
      <div className="text-center py-12 text-gray-500">
        {isProcessing && (
          <div className="w-6 h-6 border-2 border-blue-400 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
        )}
        <p className="text-sm">{msg}</p>
      </div>
    );
  }

  const charts = edaResult.charts_json;
  const missingHeatmap = charts.find((c) => c.type === "missing_heatmap");
  const distributionCharts = charts.filter(
    (c) => c.type === "histogram" || c.type === "bar_chart"
  );
  const correlationMatrix = charts.find(
    (c) => c.type === "correlation_matrix"
  );

  return (
    <div className="space-y-6">
      {missingHeatmap && (
        <MissingHeatmap data={missingHeatmap.data as MissingHeatmapItem[]} />
      )}
      {distributionCharts.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-gray-700 mb-3">
            Column Distributions
          </h3>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {distributionCharts.map((chart) => (
              <DistributionChart
                key={`${chart.type}-${chart.column}`}
                chart={chart as Chart}
              />
            ))}
          </div>
        </div>
      )}
      {correlationMatrix && (
        <CorrelationMatrix
          data={correlationMatrix.data as CorrelationMatrixData}
        />
      )}
    </div>
  );
}

function CleanPanel({
  datasetId,
  datasetVersionId,
}: {
  datasetId: string;
  datasetVersionId: string | null;
}) {
  const { data: insights } = useDatasetInsights(datasetId);
  const cleaningInsight = insights?.find(
    (i: AIInsight) => i.insight_type === "cleaning_suggestion"
  );

  return (
    <div className="space-y-6">
      {cleaningInsight && (
        <div>
          <h3 className="text-sm font-medium text-gray-700 mb-3">
            AI Suggestions (
            {(cleaningInsight.metadata_json as { actions?: unknown[] })?.actions
              ?.length ?? 0}
            )
          </h3>
          <CleaningSuggestionList
            insight={cleaningInsight}
            datasetId={datasetId}
            datasetVersionId={datasetVersionId}
          />
        </div>
      )}
      <CleaningCommandBox datasetId={datasetId} datasetVersionId={datasetVersionId} />
    </div>
  );
}

function TrainPanel({
  projectId,
  datasetId,
  datasetVersionId,
}: {
  projectId: string;
  datasetId: string;
  datasetVersionId: string | null;
}) {
  const [taskType, setTaskType] = useState<"classification" | "regression">("classification");
  const [modelType, setModelType] = useState("random_forest");
  const [targetColumn, setTargetColumn] = useState("");
  const [hyperparams, setHyperparams] = useState<Record<string, number | string>>(defaultHyperparams("random_forest"));
  const [lastRunId, setLastRunId] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [nlpCommand, setNlpCommand] = useState("");
  const [nlpConfidence, setNlpConfidence] = useState<number | null>(null);
  const [nlpError, setNlpError] = useState<string | null>(null);
  const start = useStartTraining(projectId);
  const translateTraining = useTranslateTrainingCommand();
  const { data: profile } = useDatasetProfile(datasetId);

  const modelOptions =
    taskType === "classification" ? CLASSIFICATION_MODELS : REGRESSION_MODELS;

  const handleParse = async () => {
    if (!nlpCommand.trim()) return;
    setNlpError(null);
    setNlpConfidence(null);
    try {
      const result = await translateTraining.mutateAsync({ dataset_id: datasetId, command: nlpCommand });
      if (result.task_type === "classification" || result.task_type === "regression") {
        setTaskType(result.task_type);
      }
      setModelType(result.model_type);
      // case-insensitive match against actual column names
      const cols = profile?.column_profiles?.map((c: { column_name: string }) => c.column_name) ?? [];
      const matched = cols.find((c: string) => c.toLowerCase() === result.target_column.toLowerCase()) ?? result.target_column;
      setTargetColumn(matched);
      setNlpConfidence(result.confidence);
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setNlpError(detail ?? "Failed to parse command. Please try again.");
    }
  };

  const handleStart = async () => {
    if (!datasetVersionId || !targetColumn.trim()) return;
    setSubmitError(null);
    try {
      const result = await start.mutateAsync({
        dataset_version_id: datasetVersionId,
        model_type: modelType,
        target_column: targetColumn.trim(),
        task_type: taskType,
        hyperparameters: hyperparams,
      });
      setLastRunId(result.training_run_id);
      setTargetColumn("");
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setSubmitError(detail ?? "Failed to start training. Please try again.");
    }
  };

  return (
    <div className="max-w-lg space-y-5">
      {submitError && (
        <ErrorBanner message={submitError} onDismiss={() => setSubmitError(null)} />
      )}

      {/* NLP training input */}
      <div className="bg-white border border-gray-200 rounded-xl p-5">
        <h3 className="text-sm font-semibold text-gray-800 mb-1">Describe what you want to train</h3>
        <p className="text-xs text-gray-400 mb-3">AI will parse your request and pre-fill the form below.</p>
        <textarea
          value={nlpCommand}
          onChange={(e) => setNlpCommand(e.target.value)}
          placeholder="e.g. 'predict survival using random forest for Titanic dataset'"
          rows={2}
          className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-300 resize-none"
        />
        <div className="flex items-center gap-3 mt-2">
          <button
            onClick={handleParse}
            disabled={translateTraining.isPending || !nlpCommand.trim()}
            className="text-sm px-4 py-1.5 rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {translateTraining.isPending ? "Parsing…" : "Parse"}
          </button>
          {nlpConfidence !== null && (
            <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
              nlpConfidence >= 0.8
                ? "bg-green-100 text-green-700"
                : nlpConfidence >= 0.5
                ? "bg-yellow-100 text-yellow-700"
                : "bg-red-100 text-red-700"
            }`}>
              {Math.round(nlpConfidence * 100)}% confidence
            </span>
          )}
        </div>
        {nlpError && (
          <p className="text-xs text-red-600 mt-2">{nlpError}</p>
        )}
      </div>

      <div className="bg-white border border-gray-200 rounded-xl p-5">
        <h3 className="text-sm font-semibold text-gray-800 mb-4">Train a model</h3>

        <div className="space-y-3">
          <div>
            <label className="text-xs text-gray-500 block mb-1">Task type</label>
            <div className="flex gap-2">
              {(["classification", "regression"] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => {
                    setTaskType(t);
                    const defaultModel = t === "classification" ? "random_forest" : "random_forest_regressor";
                    setModelType(defaultModel);
                    setHyperparams(defaultHyperparams(defaultModel));
                  }}
                  className={`flex-1 text-xs py-1.5 rounded-lg border transition-colors ${
                    taskType === t
                      ? "bg-blue-600 text-white border-blue-600"
                      : "border-gray-200 text-gray-600 hover:bg-gray-50"
                  }`}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="text-xs text-gray-500 block mb-1">Model</label>
            <select
              value={modelType}
              onChange={(e) => { setModelType(e.target.value); setHyperparams(defaultHyperparams(e.target.value)); }}
              className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-300"
            >
              {modelOptions.map((m) => (
                <option key={m} value={m}>
                  {MODEL_TYPE_LABELS[m]}
                </option>
              ))}
            </select>
          </div>

          <HyperparameterForm modelType={modelType} value={hyperparams} onChange={setHyperparams} />

          <div>
            <label className="text-xs text-gray-500 block mb-1">Target column</label>
            <select
              value={targetColumn}
              onChange={(e) => setTargetColumn(e.target.value)}
              className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-300"
            >
              <option value="">Select target column…</option>
              {profile?.column_profiles?.map((col: { column_name: string }) => (
                <option key={col.column_name} value={col.column_name}>
                  {col.column_name}
                </option>
              ))}
            </select>
          </div>
        </div>

        <button
          onClick={handleStart}
          disabled={start.isPending || !datasetVersionId || !targetColumn.trim()}
          className="mt-4 w-full text-sm py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          {start.isPending ? "Starting…" : "Train model"}
        </button>
      </div>

      {lastRunId && (
        <div className="bg-green-50 border border-green-200 rounded-xl p-4 text-sm text-green-700">
          Training started.{" "}
          <Link
            href={`/projects/${projectId}/training/${lastRunId}`}
            className="font-medium underline"
          >
            View run →
          </Link>
        </div>
      )}
    </div>
  );
}

export default function DatasetWorkspacePage() {
  const { projectId, datasetId } = useParams<{
    projectId: string;
    datasetId: string;
  }>();
  const { data: dataset } = useDataset(datasetId);
  const { data: versions } = useDatasetVersions(datasetId);
  const deleteVersion = useDeleteDatasetVersion(datasetId);
  const [tab, setTab] = useState<Tab>("profile");

  const sortedVersions = versions ? [...versions].sort((a, b) => b.version_number - a.version_number) : [];
  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(null);
  const activeVersionId = selectedVersionId ?? sortedVersions[0]?.id ?? null;

  // Auto-select newest when versions load
  useEffect(() => {
    if (sortedVersions.length > 0 && !selectedVersionId) {
      setSelectedVersionId(sortedVersions[0].id);
    }
  }, [sortedVersions.length]);

  const navItems = [{ label: "Overview", href: `/projects/${projectId}` }];

  return (
    <AppShell sideNavItems={navItems}>
      <div className="flex h-full">
        {/* Main content */}
        <div className="flex-1 overflow-auto p-6">
          <div className="max-w-5xl mx-auto">
            <div className="mb-6">
              <h1 className="text-xl font-semibold text-gray-900">
                {dataset?.name ?? "Loading…"}
              </h1>
              <p className="text-sm text-gray-500 mt-0.5">
                {dataset?.original_file_name} &middot;{" "}
                {dataset?.file_format?.toUpperCase()}
                {dataset?.row_count != null &&
                  ` · ${dataset.row_count.toLocaleString()} rows`}
                {dataset?.column_count != null &&
                  ` · ${dataset.column_count} cols`}
              </p>
            </div>

            {sortedVersions.length > 0 && (
              <div className="flex items-center gap-2 mb-4 bg-white border border-gray-200 rounded-xl px-4 py-2">
                <span className="text-xs text-gray-500 shrink-0">Working on:</span>
                <select
                  value={activeVersionId ?? ""}
                  onChange={(e) => setSelectedVersionId(e.target.value)}
                  className="text-xs border border-gray-200 rounded-lg px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-300"
                >
                  {sortedVersions.map((v) => (
                    <option key={v.id} value={v.id}>
                      v{v.version_number} — {new Date(v.created_at).toLocaleString()}
                      {v.row_count != null ? ` (${v.row_count.toLocaleString()} rows)` : ""}
                    </option>
                  ))}
                </select>
                {selectedVersionId && selectedVersionId !== sortedVersions[0]?.id && (
                  <span className="text-xs text-yellow-600 bg-yellow-50 px-2 py-0.5 rounded-full">
                    Not latest version
                  </span>
                )}
                {activeVersionId && sortedVersions.find(v => v.id === activeVersionId)?.version_number !== 0 && (
                  <button
                    onClick={() => {
                      if (!activeVersionId) return;
                      const v = sortedVersions.find(v => v.id === activeVersionId);
                      if (!confirm(`Delete v${v?.version_number}? This cannot be undone.`)) return;
                      deleteVersion.mutate(activeVersionId);
                      setSelectedVersionId(null);
                    }}
                    disabled={deleteVersion.isPending}
                    className="ml-auto text-xs text-red-500 hover:text-red-700 hover:bg-red-50 px-2 py-1 rounded-lg disabled:opacity-40"
                    title="Delete this version"
                  >
                    Delete version
                  </button>
                )}
              </div>
            )}

            <div className="flex gap-4 border-b border-gray-200 mb-6">
              {(["profile", "eda", "clean", "history", "train", "preview"] as Tab[]).map((t) => (
                <button
                  key={t}
                  onClick={() => setTab(t)}
                  className={`pb-3 text-sm font-medium border-b-2 transition-colors ${
                    tab === t
                      ? "border-blue-600 text-blue-600"
                      : "border-transparent text-gray-500 hover:text-gray-700"
                  }`}
                >
                  {t === "profile"
                    ? "Profile"
                    : t === "eda"
                    ? "EDA"
                    : t === "clean"
                    ? "Clean"
                    : t === "history"
                    ? "History"
                    : t === "train"
                    ? "Train"
                    : "Data Preview"}
                </button>
              ))}
            </div>

            <ErrorBoundary>
              {tab === "profile" && (
                <ProfileComparisonPanel datasetId={datasetId} activeVersionId={activeVersionId} />
              )}
            </ErrorBoundary>
            <ErrorBoundary>
              {tab === "eda" && (
                <EdaPanel datasetVersionId={activeVersionId} />
              )}
            </ErrorBoundary>
            <ErrorBoundary>
              {tab === "clean" && (
                <CleanPanel datasetId={datasetId} datasetVersionId={activeVersionId} />
              )}
            </ErrorBoundary>
            <ErrorBoundary>
              {tab === "history" && (
                <CleaningHistoryPanel datasetId={datasetId} />
              )}
            </ErrorBoundary>
            <ErrorBoundary>
              {tab === "train" && (
                <TrainPanel projectId={projectId} datasetId={datasetId} datasetVersionId={activeVersionId} />
              )}
            </ErrorBoundary>
            <ErrorBoundary>
              {tab === "preview" &&
                (dataset?.status === "ready" ? (
                  <div>
                    <div className="flex justify-end mb-3">
                      <button
                        onClick={() => {
                          if (!activeVersionId) return;
                          const url = `${process.env.NEXT_PUBLIC_API_URL}/datasets/${datasetId}/versions/${activeVersionId}/export`;
                          fetch(url, { headers: { Authorization: `Bearer ${localStorage.getItem("access_token")}` } })
                            .then((r) => {
                              const cd = r.headers.get("Content-Disposition") ?? "";
                              const match = cd.match(/filename="?([^"]+)"?/);
                              const filename = match?.[1] ?? "dataset_export.csv";
                              return r.blob().then((blob) => ({ blob, filename }));
                            })
                            .then(({ blob, filename }) => {
                              const objUrl = URL.createObjectURL(blob);
                              const a = document.createElement("a");
                              a.href = objUrl;
                              a.download = filename;
                              a.click();
                              URL.revokeObjectURL(objUrl);
                            });
                        }}
                        className="text-xs px-3 py-1.5 rounded-lg bg-gray-100 text-gray-700 hover:bg-gray-200"
                      >
                        ↓ Export CSV
                      </button>
                    </div>
                    <DatasetPreviewTable datasetId={datasetId} versionId={activeVersionId} />
                  </div>
                ) : (
                  <div className="text-center py-12 text-gray-500">
                    <p>Dataset is still being processed…</p>
                  </div>
                ))}
            </ErrorBoundary>
          </div>
        </div>

        {/* AI Sidebar */}
        {dataset && (
          <AIAssistantSidebar
            datasetId={datasetId}
            datasetStatus={dataset.status}
          />
        )}
      </div>
    </AppShell>
  );
}
