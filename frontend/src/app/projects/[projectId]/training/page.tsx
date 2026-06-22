"use client";
import { useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { AppShell } from "@/components/layout/AppShell";
import { useProjectTrainingRuns, useStartTraining } from "@/lib/hooks/useTraining";
import { useDatasets, useDatasetVersions, useDatasetProfile } from "@/lib/hooks/useDatasets";
import {
  MODEL_TYPE_LABELS,
  CLASSIFICATION_MODELS,
  REGRESSION_MODELS,
} from "@/lib/api/training";
import { ErrorBanner } from "@/components/shared/ErrorBanner";
import { HyperparameterForm, defaultHyperparams } from "@/components/training/HyperparameterForm";

const STATUS_COLORS: Record<string, string> = {
  succeeded: "bg-green-100 text-green-700",
  running: "bg-blue-100 text-blue-700",
  queued: "bg-yellow-100 text-yellow-700",
  failed: "bg-red-100 text-red-700",
};

function StartTrainingForm({
  projectId,
  onClose,
}: {
  projectId: string;
  onClose: () => void;
}) {
  const { data: datasets } = useDatasets(projectId);
  const [selectedDatasetId, setSelectedDatasetId] = useState("");
  const { data: versions } = useDatasetVersions(selectedDatasetId);
  const { data: profile } = useDatasetProfile(selectedDatasetId);
  const [taskType, setTaskType] = useState<"classification" | "regression">(
    "classification"
  );
  const [modelType, setModelType] = useState("random_forest");
  const [targetColumn, setTargetColumn] = useState("");
  const [hyperparams, setHyperparams] = useState<Record<string, number | string>>(defaultHyperparams("random_forest"));
  const [submitError, setSubmitError] = useState<string | null>(null);
  const start = useStartTraining(projectId);

  const latestVersionId =
    versions && versions.length > 0
      ? [...versions].sort((a, b) => b.version_number - a.version_number)[0].id
      : null;

  const modelOptions =
    taskType === "classification" ? CLASSIFICATION_MODELS : REGRESSION_MODELS;

  const handleSubmit = async () => {
    if (!latestVersionId || !targetColumn.trim() || !modelType) return;
    setSubmitError(null);
    try {
      await start.mutateAsync({
        dataset_version_id: latestVersionId,
        model_type: modelType,
        target_column: targetColumn.trim(),
        task_type: taskType,
        hyperparameters: hyperparams,
      });
      onClose();
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setSubmitError(detail ?? "Failed to start training. Please try again.");
    }
  };

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-5 mb-5">
      <h3 className="text-sm font-semibold text-gray-800 mb-4">
        Start training run
      </h3>

      {submitError && (
        <ErrorBanner message={submitError} onDismiss={() => setSubmitError(null)} />
      )}

      <div className="space-y-3">
        <div>
          <label className="text-xs text-gray-500 block mb-1">Dataset</label>
          <select
            value={selectedDatasetId}
            onChange={(e) => { setSelectedDatasetId(e.target.value); setTargetColumn(""); }}
            className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-300"
          >
            <option value="">Select dataset…</option>
            {datasets
              ?.filter((d) => d.status === "ready")
              .map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
          </select>
        </div>

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
          <label className="text-xs text-gray-500 block mb-1">
            Target column
          </label>
          <select
            value={targetColumn}
            onChange={(e) => setTargetColumn(e.target.value)}
            className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-300"
            disabled={!selectedDatasetId}
          >
            <option value="">
              {selectedDatasetId ? "Select target column…" : "Select dataset first"}
            </option>
            {profile?.column_profiles?.map((col: { column_name: string }) => (
              <option key={col.column_name} value={col.column_name}>
                {col.column_name}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="flex gap-2 mt-4">
        <button
          onClick={handleSubmit}
          disabled={
            start.isPending || !latestVersionId || !targetColumn.trim()
          }
          className="text-sm px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          {start.isPending ? "Starting…" : "Start training"}
        </button>
        <button
          onClick={onClose}
          className="text-sm px-3 py-2 border border-gray-200 text-gray-600 rounded-lg hover:bg-gray-50"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

export default function TrainingPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { data: runs, isLoading } = useProjectTrainingRuns(projectId);
  const [showForm, setShowForm] = useState(false);
  const navItems = [{ label: "Overview", href: `/projects/${projectId}` }];

  return (
    <AppShell sideNavItems={navItems}>
      <div className="max-w-4xl mx-auto p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <Link
              href={`/projects/${projectId}`}
              className="text-xs text-gray-400 hover:text-gray-600 mb-1 block"
            >
              ← Project overview
            </Link>
            <h1 className="text-xl font-semibold text-gray-900">
              Training Runs
            </h1>
          </div>
          <button
            onClick={() => setShowForm(true)}
            className="text-sm bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
          >
            New training run
          </button>
        </div>

        {showForm && (
          <StartTrainingForm
            projectId={projectId}
            onClose={() => setShowForm(false)}
          />
        )}

        {isLoading ? (
          <div className="space-y-2">
            {[1, 2].map((i) => (
              <div
                key={i}
                className="h-16 bg-gray-100 rounded-xl animate-pulse"
              />
            ))}
          </div>
        ) : runs?.length === 0 ? (
          <div className="text-center py-12 bg-white border border-dashed border-gray-300 rounded-xl text-gray-500">
            <p className="font-medium">No training runs yet</p>
            <p className="text-sm mt-1">
              Start a run to train your first model.
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {runs?.map((r) => (
              <div key={r.id}>
                <Link
                  href={`/projects/${projectId}/training/${r.id}`}
                  className="flex items-center justify-between bg-white border border-gray-200 rounded-xl px-5 py-4 hover:border-blue-400 transition-colors"
                >
                  <div>
                    <p className="font-medium text-gray-900">
                      {MODEL_TYPE_LABELS[r.model_type] ?? r.model_type}
                    </p>
                    <p className="text-xs text-gray-400 mt-0.5">
                      {r.task_type} · target:{" "}
                      <code className="bg-gray-100 px-1 rounded">
                        {r.selected_target_column}
                      </code>
                      {r.metrics.length > 0 && (
                        <>
                          {" · "}
                          {r.metrics[0].metric_name}:{" "}
                          {r.metrics[0].metric_value.toFixed(3)}
                        </>
                      )}
                    </p>
                  </div>
                  <span
                    className={`text-xs font-medium px-2 py-1 rounded-full ${
                      STATUS_COLORS[r.train_status] ?? "bg-gray-100 text-gray-600"
                    }`}
                  >
                    {r.train_status}
                  </span>
                </Link>
                {r.train_status === "failed" && r.error_message && (
                  <details className="mt-1 px-5">
                    <summary className="text-xs text-red-500 cursor-pointer select-none">
                      ▸ Show error
                    </summary>
                    <p className="text-xs text-red-600 mt-1 bg-red-50 border border-red-100 rounded-lg px-3 py-2">
                      {r.error_message}
                    </p>
                  </details>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}
