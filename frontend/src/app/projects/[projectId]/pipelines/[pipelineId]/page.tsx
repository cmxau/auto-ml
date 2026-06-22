"use client";
import { useParams } from "next/navigation";
import Link from "next/link";
import { AppShell } from "@/components/layout/AppShell";
import { PipelineCanvas } from "@/components/pipeline/PipelineCanvas";
import { usePipeline, usePipelineRuns, useStartPipelineRun } from "@/lib/hooks/usePipeline";

export default function PipelineEditorPage() {
  const { projectId, pipelineId } = useParams<{
    projectId: string;
    pipelineId: string;
  }>();
  const { data: pipeline, isLoading } = usePipeline(pipelineId);
  const runs = usePipelineRuns(pipelineId);
  const startRun = useStartPipelineRun(pipelineId);

  const navItems = [{ label: "Overview", href: `/projects/${projectId}` }];

  return (
    <AppShell sideNavItems={navItems}>
      <div className="flex flex-col h-full">
        {/* Header */}
        <div className="shrink-0 border-b border-gray-200 bg-white px-5 py-3 flex items-center gap-3">
          <Link
            href={`/projects/${projectId}/pipelines`}
            className="text-xs text-gray-400 hover:text-gray-600"
          >
            ← Pipelines
          </Link>
          <span className="text-gray-300">|</span>
          <h1 className="text-sm font-semibold text-gray-900">
            {pipeline?.name ?? "Loading…"}
          </h1>
          {pipeline?.status && (
            <span
              className={`text-xs font-medium px-2 py-0.5 rounded-full ml-1 ${
                pipeline.status === "valid"
                  ? "bg-green-100 text-green-700"
                  : pipeline.status === "invalid"
                  ? "bg-red-100 text-red-700"
                  : "bg-gray-100 text-gray-600"
              }`}
            >
              {pipeline.status}
            </span>
          )}
          <div className="ml-auto">
            <button
              onClick={() => startRun.mutate()}
              disabled={startRun.isPending}
              className="text-sm px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
            >
              {startRun.isPending ? "Starting…" : "▶ Run pipeline"}
            </button>
          </div>
        </div>

        {/* Canvas */}
        <div className="flex-1 overflow-hidden">
          {isLoading || !pipeline ? (
            <div className="flex items-center justify-center h-full text-gray-400 text-sm">
              Loading pipeline…
            </div>
          ) : (
            <PipelineCanvas pipeline={pipeline} projectId={projectId} />
          )}
        </div>

        {/* Run history */}
        <div className="shrink-0 border-t border-gray-200 bg-gray-50 px-5 py-4">
          <h3 className="text-sm font-semibold text-gray-800 mb-3">Run history</h3>
          {runs.data?.length === 0 && (
            <p className="text-sm text-gray-400">No runs yet.</p>
          )}
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {runs.data?.map(run => (
              <div
                key={run.id}
                className="flex items-center gap-3 bg-white border border-gray-200 rounded-xl px-4 py-3 text-sm"
              >
                <span
                  className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                    run.status === "succeeded"
                      ? "bg-green-100 text-green-700"
                      : run.status === "failed"
                      ? "bg-red-100 text-red-700"
                      : run.status === "running"
                      ? "bg-blue-100 text-blue-700"
                      : "bg-yellow-100 text-yellow-700"
                  }`}
                >
                  {run.status}
                </span>
                <span className="text-gray-500 text-xs">
                  {new Date(run.created_at).toLocaleString()}
                </span>
                {run.error_message && (
                  <span className="text-xs text-red-500 truncate">{run.error_message}</span>
                )}
                {run.completed_at && (
                  <span className="text-xs text-gray-400 ml-auto">
                    {((new Date(run.completed_at).getTime() - new Date(run.created_at).getTime()) / 1000).toFixed(1)}s
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
