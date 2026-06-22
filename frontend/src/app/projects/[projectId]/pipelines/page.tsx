"use client";
import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { AppShell } from "@/components/layout/AppShell";
import { usePipelineList, useCreatePipeline, useDeletePipeline } from "@/lib/hooks/usePipeline";
import { useDatasets } from "@/lib/hooks/useDatasets";
import { useMutation } from "@tanstack/react-query";
import { aiApi } from "@/lib/api/ai";

export default function PipelinesPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const router = useRouter();
  const { data: pipelines, isLoading } = usePipelineList(projectId);
  const { data: datasets } = useDatasets(projectId);
  const create = useCreatePipeline(projectId);
  const deletePipeline = useDeletePipeline(projectId);
  const [newName, setNewName] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [showAI, setShowAI] = useState(false);
  const [aiDatasetId, setAiDatasetId] = useState("");
  const [aiError, setAiError] = useState<string | null>(null);

  const recommendPipeline = useMutation({
    mutationFn: async (datasetId: string) =>
      (await aiApi.recommendPipeline({ dataset_id: datasetId, project_id: projectId })).data.data,
    onSuccess: (data) => router.push(`/projects/${projectId}/pipelines/${data.pipeline_id}`),
    onError: (e: unknown) => {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setAiError(detail ?? "AI recommendation failed");
    },
  });

  const navItems = [{ label: "Overview", href: `/projects/${projectId}` }];

  const handleCreate = async () => {
    if (!newName.trim()) return;
    const pipeline = await create.mutateAsync({ name: newName.trim() });
    router.push(`/projects/${projectId}/pipelines/${pipeline.id}`);
  };

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
            <h1 className="text-xl font-semibold text-gray-900">Pipelines</h1>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => { setShowAI(true); setShowCreate(false); setAiError(null); }}
              className="text-sm bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700"
            >
              ✨ AI pipeline
            </button>
            <button
              onClick={() => { setShowCreate(true); setShowAI(false); }}
              className="text-sm bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
            >
              New pipeline
            </button>
          </div>
        </div>

        {showAI && (
          <div className="bg-white border border-purple-200 rounded-xl p-4 mb-4">
            <h3 className="text-sm font-semibold text-gray-800 mb-1">Generate AI pipeline</h3>
            <p className="text-xs text-gray-500 mb-3">AI will analyse the dataset profile and design an optimal pipeline.</p>
            {aiError && <p className="text-xs text-red-600 mb-2">{aiError}</p>}
            <div className="flex gap-2">
              <select
                value={aiDatasetId}
                onChange={(e) => setAiDatasetId(e.target.value)}
                className="flex-1 text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-purple-300"
              >
                <option value="">Select dataset…</option>
                {datasets?.filter(d => d.status === "ready").map(d => (
                  <option key={d.id} value={d.id}>{d.name}</option>
                ))}
              </select>
              <button
                onClick={() => recommendPipeline.mutate(aiDatasetId)}
                disabled={!aiDatasetId || recommendPipeline.isPending}
                className="text-sm px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
              >
                {recommendPipeline.isPending ? "Generating…" : "Generate"}
              </button>
              <button
                onClick={() => { setShowAI(false); setAiDatasetId(""); setAiError(null); }}
                className="text-sm px-3 py-2 border border-gray-200 rounded-lg text-gray-600 hover:bg-gray-50"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {showCreate && (
          <div className="bg-white border border-gray-200 rounded-xl p-4 mb-4">
            <h3 className="text-sm font-semibold text-gray-800 mb-3">
              Create pipeline
            </h3>
            <div className="flex gap-2">
              <input
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleCreate()}
                placeholder="Pipeline name"
                autoFocus
                className="flex-1 text-sm border border-gray-200 rounded-lg px-3 py-2
                  focus:outline-none focus:ring-2 focus:ring-blue-300"
              />
              <button
                onClick={handleCreate}
                disabled={create.isPending || !newName.trim()}
                className="text-sm px-4 py-2 bg-blue-600 text-white rounded-lg
                  hover:bg-blue-700 disabled:opacity-50"
              >
                {create.isPending ? "Creating…" : "Create"}
              </button>
              <button
                onClick={() => {
                  setShowCreate(false);
                  setNewName("");
                }}
                className="text-sm px-3 py-2 border border-gray-200 rounded-lg
                  text-gray-600 hover:bg-gray-50"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {isLoading ? (
          <div className="space-y-2">
            {[1, 2].map((i) => (
              <div key={i} className="h-16 bg-gray-100 rounded-xl animate-pulse" />
            ))}
          </div>
        ) : pipelines?.length === 0 ? (
          <div className="text-center py-12 bg-white border border-dashed border-gray-300 rounded-xl text-gray-500">
            <p className="font-medium">No pipelines yet</p>
            <p className="text-sm mt-1">
              Create a pipeline to start building your ML workflow.
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {pipelines?.map((p) => (
              <div key={p.id} className="relative group bg-white border border-gray-200 rounded-xl hover:border-blue-400 transition-colors">
                <Link
                  href={`/projects/${projectId}/pipelines/${p.id}`}
                  className="flex items-center justify-between px-5 py-4 pr-12"
                >
                  <div>
                    <p className="font-medium text-gray-900">{p.name}</p>
                    <p className="text-xs text-gray-400 mt-0.5">
                      {p.nodes.length} nodes · {p.edges.length} edges
                    </p>
                  </div>
                  <span
                    className={`text-xs font-medium px-2 py-1 rounded-full ${
                      p.status === "valid"
                        ? "bg-green-100 text-green-700"
                        : p.status === "invalid"
                        ? "bg-red-100 text-red-700"
                        : "bg-gray-100 text-gray-600"
                    }`}
                  >
                    {p.status}
                  </span>
                </Link>
                <button
                  onClick={(e) => {
                    e.preventDefault();
                    if (!confirm(`Delete "${p.name}"? This cannot be undone.`)) return;
                    deletePipeline.mutate(p.id);
                  }}
                  disabled={deletePipeline.isPending}
                  className="absolute top-3 right-3 p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-md opacity-0 group-hover:opacity-100 transition-opacity disabled:opacity-30"
                  title="Delete pipeline"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
                  </svg>
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}
