"use client";

import { AppShell } from "@/components/layout/AppShell";
import { useProject, useUpdateProject } from "@/lib/hooks/useProjects";
import { useDatasets, useDeleteDataset, useReplaceDataset } from "@/lib/hooks/useDatasets";
import { usePipelineList } from "@/lib/hooks/usePipeline";
import { useProjectTrainingRuns } from "@/lib/hooks/useTraining";
import { MODEL_TYPE_LABELS } from "@/lib/api/training";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

export default function ProjectPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { data: project } = useProject(projectId);
  const { data: datasets, isLoading } = useDatasets(projectId);
  const { data: pipelines } = usePipelineList(projectId);
  const { data: trainingRuns } = useProjectTrainingRuns(projectId);
  const updateProject = useUpdateProject(projectId);
  const deleteDataset = useDeleteDataset(projectId);
  const replaceDataset = useReplaceDataset(projectId);

  const [editingName, setEditingName] = useState(false);
  const [nameInput, setNameInput] = useState("");

  const startEdit = () => {
    setNameInput(project?.name ?? "");
    setEditingName(true);
  };

  const cancelEdit = () => setEditingName(false);

  const saveName = async () => {
    if (!nameInput.trim()) return;
    await updateProject.mutateAsync({ name: nameInput.trim() });
    setEditingName(false);
  };

  const handleDeleteDataset = (e: React.MouseEvent, id: string, name: string) => {
    e.preventDefault();
    if (!confirm(`Delete "${name}"? This cannot be undone.`)) return;
    deleteDataset.mutate(id);
  };

  const navItems = [
    { label: "Overview", href: `/projects/${projectId}` },
  ];

  return (
    <AppShell sideNavItems={navItems}>
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center gap-3 mb-1">
          {editingName ? (
            <div className="flex items-center gap-2 flex-1">
              <input
                autoFocus
                value={nameInput}
                onChange={(e) => setNameInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") saveName();
                  if (e.key === "Escape") cancelEdit();
                }}
                className="text-2xl font-semibold text-gray-900 border border-gray-300 rounded-lg px-2 py-0.5 focus:outline-none focus:ring-2 focus:ring-blue-500 flex-1"
              />
              <button
                onClick={saveName}
                disabled={updateProject.isPending}
                className="text-sm bg-blue-600 text-white px-3 py-1 rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                Save
              </button>
              <button
                onClick={cancelEdit}
                className="text-sm text-gray-500 px-3 py-1 rounded-lg hover:bg-gray-100"
              >
                Cancel
              </button>
            </div>
          ) : (
            <>
              <h1 className="text-2xl font-semibold text-gray-900">
                {project?.name ?? "Loading…"}
              </h1>
              {project && (
                <button
                  onClick={startEdit}
                  className="text-gray-400 hover:text-gray-700 p-1 rounded transition-colors"
                  title="Edit project name"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                    <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
                  </svg>
                </button>
              )}
            </>
          )}
        </div>
        {project?.description && (
          <p className="text-gray-500 text-sm mb-6">{project.description}</p>
        )}

        <div className="mt-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-medium text-gray-800">Datasets</h2>
            <Link
              href={`/projects/${projectId}/datasets/upload`}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700"
            >
              Upload dataset
            </Link>
          </div>

          {isLoading ? (
            <div className="space-y-2">
              {[1, 2].map((i) => (
                <div key={i} className="h-16 bg-gray-100 rounded-xl animate-pulse" />
              ))}
            </div>
          ) : datasets?.length === 0 ? (
            <div className="text-center py-12 bg-white border border-dashed border-gray-300 rounded-xl text-gray-500">
              <p className="font-medium">No datasets yet</p>
              <p className="text-sm mt-1">Upload a CSV or XLSX file to get started.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {datasets?.map((ds) => (
                <div
                  key={ds.id}
                  className="relative bg-white border border-gray-200 rounded-xl hover:border-blue-400 transition-colors group"
                >
                  <Link
                    href={`/projects/${projectId}/datasets/${ds.id}`}
                    className="flex items-center justify-between px-5 py-4 pr-12"
                  >
                    <div>
                      <p className="font-medium text-gray-900">{ds.name}</p>
                      <p className="text-xs text-gray-400 mt-0.5">
                        {ds.original_file_name} &middot; {ds.file_format.toUpperCase()}
                        {ds.row_count != null &&
                          ` · ${ds.row_count.toLocaleString()} rows`}
                      </p>
                    </div>
                    <span
                      className={`text-xs font-medium px-2 py-1 rounded-full ${
                        ds.status === "ready"
                          ? "bg-green-100 text-green-700"
                          : ds.status === "failed"
                          ? "bg-red-100 text-red-700"
                          : "bg-yellow-100 text-yellow-700"
                      }`}
                    >
                      {ds.status}
                    </span>
                  </Link>
                  <div className="absolute top-3 right-3 flex items-center gap-1">
                    <label
                      className="text-xs px-2 py-1.5 rounded-lg text-blue-600 hover:bg-blue-50 cursor-pointer opacity-0 group-hover:opacity-100 transition-opacity"
                      title="Replace file"
                    >
                      ↑
                      <input
                        type="file"
                        accept=".csv,.xlsx,.json"
                        className="hidden"
                        onChange={(e) => {
                          const f = e.target.files?.[0];
                          if (f && window.confirm(`Replace "${ds.name}" with "${f.name}"?`)) {
                            replaceDataset.mutate({ datasetId: ds.id, file: f });
                          }
                          e.target.value = "";
                        }}
                      />
                    </label>
                    <button
                      onClick={(e) => handleDeleteDataset(e, ds.id, ds.name)}
                      disabled={deleteDataset.isPending}
                      className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-md opacity-0 group-hover:opacity-100 transition-opacity disabled:opacity-30"
                      title="Delete dataset"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
                      </svg>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="mt-10">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-medium text-gray-800">Pipelines</h2>
            <Link
              href={`/projects/${projectId}/pipelines`}
              className="bg-white border border-gray-200 text-gray-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-50"
            >
              View all pipelines
            </Link>
          </div>

          {!pipelines || pipelines.length === 0 ? (
            <div className="text-center py-8 bg-white border border-dashed border-gray-300 rounded-xl text-gray-500">
              <p className="text-sm">No pipelines yet.</p>
              <Link
                href={`/projects/${projectId}/pipelines`}
                className="text-sm text-blue-600 hover:underline mt-1 block"
              >
                Create a pipeline →
              </Link>
            </div>
          ) : (
            <div className="space-y-2">
              {pipelines.slice(0, 3).map((p) => (
                <Link
                  key={p.id}
                  href={`/projects/${projectId}/pipelines/${p.id}`}
                  className="flex items-center justify-between bg-white border border-gray-200 rounded-xl px-5 py-3 hover:border-blue-400 transition-colors"
                >
                  <p className="text-sm font-medium text-gray-900">{p.name}</p>
                  <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                    p.status === "valid"
                      ? "bg-green-100 text-green-700"
                      : p.status === "invalid"
                      ? "bg-red-100 text-red-700"
                      : "bg-gray-100 text-gray-600"
                  }`}>
                    {p.status}
                  </span>
                </Link>
              ))}
            </div>
          )}
        </div>
        <div className="mt-10">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-medium text-gray-800">Training Runs</h2>
            <Link
              href={`/projects/${projectId}/training`}
              className="bg-white border border-gray-200 text-gray-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-50"
            >
              View all runs
            </Link>
          </div>

          {!trainingRuns || trainingRuns.length === 0 ? (
            <div className="text-center py-8 bg-white border border-dashed border-gray-300 rounded-xl text-gray-500">
              <p className="text-sm">No training runs yet.</p>
              <Link
                href={`/projects/${projectId}/training`}
                className="text-sm text-blue-600 hover:underline mt-1 block"
              >
                Start training →
              </Link>
            </div>
          ) : (
            <div className="space-y-2">
              {trainingRuns.slice(0, 3).map((r) => (
                <Link
                  key={r.id}
                  href={`/projects/${projectId}/training/${r.id}`}
                  className="flex items-center justify-between bg-white border border-gray-200 rounded-xl px-5 py-3 hover:border-blue-400 transition-colors"
                >
                  <div>
                    <p className="text-sm font-medium text-gray-900">
                      {MODEL_TYPE_LABELS[r.model_type] ?? r.model_type}
                    </p>
                    <p className="text-xs text-gray-400 mt-0.5">
                      target: {r.selected_target_column}
                    </p>
                  </div>
                  <span
                    className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                      r.train_status === "succeeded"
                        ? "bg-green-100 text-green-700"
                        : r.train_status === "failed"
                        ? "bg-red-100 text-red-700"
                        : r.train_status === "running"
                        ? "bg-blue-100 text-blue-700"
                        : "bg-gray-100 text-gray-600"
                    }`}
                  >
                    {r.train_status}
                  </span>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
