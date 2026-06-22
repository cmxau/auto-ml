"use client";
import { useMemo, useState } from "react";
import type { AIInsight } from "@/lib/api/ai";
import type { CleaningAction, PreviewResult } from "@/lib/api/cleaning";
import { usePreviewAction, useApplyAction, useCleaningHistory } from "@/lib/hooks/useCleaning";
import { cleaningApi } from "@/lib/api/cleaning";
import { datasetsApi } from "@/lib/api/datasets";
import { useDatasetVersions, useWaitForNewVersion } from "@/lib/hooks/useDatasets";
import { CleaningConfirmModal } from "./CleaningConfirmModal";
import { extractApiError } from "@/lib/api/client";

interface SuggestedActionRaw {
  action_type: string;
  column?: string;
  reason: string;
  priority: "high" | "medium" | "low";
  destructive: boolean;
  method?: string;
  parameters?: Record<string, unknown>;
}

function buildAction(raw: SuggestedActionRaw): CleaningAction {
  const params: Record<string, unknown> = { ...(raw.parameters ?? {}) };
  if (raw.column && !params.column) params.column = raw.column;
  if (raw.method && !params.method) params.method = raw.method;
  return {
    action_type: raw.action_type,
    parameters: params,
    title: `${raw.action_type.replace(/_/g, " ")}: ${raw.column ?? ""}`.trim(),
    description: raw.reason,
    suggested_by: "ai",
  };
}

const PRIORITY_COLORS: Record<string, string> = {
  high: "text-red-500",
  medium: "text-yellow-500",
  low: "text-gray-400",
};

interface Props {
  insight: AIInsight;
  datasetId: string;
  datasetVersionId: string | null;
}

export function CleaningSuggestionList({ insight, datasetId, datasetVersionId }: Props) {
  const meta = (insight.metadata_json ?? {}) as { actions?: SuggestedActionRaw[] };
  const rawActions = meta.actions ?? [];

  const preview = usePreviewAction(datasetVersionId);
  const apply = useApplyAction(datasetId, datasetVersionId);
  const { data: versions } = useDatasetVersions(datasetId);
  const { data: cleaningHistory } = useCleaningHistory(datasetId);

  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [dismissed, setDismissed] = useState<Set<number>>(new Set());
  const [applied, setApplied] = useState<Set<number>>(new Set());

  // Cross-reference rawActions with backend history to persist applied state across reloads
  const persistedApplied = useMemo<Set<number>>(() => {
    if (!cleaningHistory || cleaningHistory.length === 0) return new Set();
    const result = new Set<number>();
    rawActions.forEach((raw, idx) => {
      const match = cleaningHistory.some(
        (item) =>
          item.action.status === "applied" &&
          item.action.action_type === raw.action_type &&
          (item.action.parameters_json as Record<string, unknown>)?.column === raw.column
      );
      if (match) result.add(idx);
    });
    return result;
  }, [cleaningHistory, rawActions]);

  const effectiveApplied = useMemo(
    () => new Set([...applied, ...persistedApplied]),
    [applied, persistedApplied]
  );

  // single-action preview flow
  const [pending, setPending] = useState<{ action: CleaningAction; previewResult: PreviewResult; idx: number } | null>(null);

  // multi-apply state
  const [applyingMulti, setApplyingMulti] = useState(false);
  const [multiProgress, setMultiProgress] = useState<string | null>(null);

  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [baselineVersionCount, setBaselineVersionCount] = useState<number | null>(null);

  useWaitForNewVersion(datasetId, baselineVersionCount, () => {
    setSuccessMsg("New dataset version is ready!");
    setBaselineVersionCount(null);
  });

  if (rawActions.length === 0) {
    return <p className="text-sm text-gray-400">No suggestions available.</p>;
  }

  const unappliedIndices = rawActions
    .map((_, i) => i)
    .filter((i) => !dismissed.has(i) && !effectiveApplied.has(i));

  const toggleSelect = (idx: number) => {
    setSelected((s) => {
      const next = new Set(s);
      next.has(idx) ? next.delete(idx) : next.add(idx);
      return next;
    });
  };

  const toggleSelectAll = () => {
    const selectableUnapplied = unappliedIndices.filter((i) => !effectiveApplied.has(i));
    const allSelected = selectableUnapplied.every((i) => selected.has(i));
    setSelected(allSelected ? new Set() : new Set(selectableUnapplied));
  };

  const handlePreview = async (raw: SuggestedActionRaw, idx: number) => {
    setErrorMsg(null);
    try {
      const result = await preview.mutateAsync(buildAction(raw));
      setPending({ action: buildAction(raw), previewResult: result, idx });
    } catch (e) {
      setErrorMsg(`Preview failed: ${extractApiError(e)}`);
    }
  };

  const handleSingleApply = async () => {
    if (!pending) return;
    setErrorMsg(null);
    try {
      const currentCount = versions?.length ?? 0;
      await apply.mutateAsync(pending.action);
      setApplied((a) => { const next = new Set(a); next.add(pending.idx); return next; });
      setSelected((s) => { const next = new Set(s); next.delete(pending.idx); return next; });
      setPending(null);
      setBaselineVersionCount(currentCount);
      setSuccessMsg("Transformation queued — waiting for new version…");
    } catch (e) {
      setErrorMsg(`Apply failed: ${extractApiError(e)}`);
    }
  };

  const handleApplySelected = async () => {
    const toApply = [...selected].filter((i) => !effectiveApplied.has(i));
    if (toApply.length === 0) return;
    setApplyingMulti(true);
    setErrorMsg(null);

    // Chain: each action applies to the version produced by the previous one
    let chainVersionId = datasetVersionId;
    let successCount = 0;

    for (const idx of toApply) {
      setMultiProgress(`Applying ${successCount + 1} / ${toApply.length} — chaining on latest version…`);
      try {
        if (!chainVersionId) throw new Error("No version ID available");

        // Apply directly via API with the current chain version
        await cleaningApi.apply(chainVersionId, { ...buildAction(rawActions[idx]), suggested_by: "ai" });
        setApplied((a) => { const next = new Set(a); next.add(idx); return next; });
        successCount++;

        // Poll until a new version appears, then use it as next chain input
        if (successCount < toApply.length) {
          setMultiProgress(`Waiting for v${successCount + 1} to be ready…`);
          const deadline = Date.now() + 30000;
          while (Date.now() < deadline) {
            await new Promise(r => setTimeout(r, 1500));
            const res = await datasetsApi.versions(datasetId);
            const allVersions = res.data.data;
            const newest = [...allVersions].sort((a, b) => b.version_number - a.version_number)[0];
            if (newest && newest.id !== chainVersionId) {
              chainVersionId = newest.id;
              break;
            }
          }
        }
      } catch (e) {
        setErrorMsg(`Failed on "${rawActions[idx].action_type}": ${extractApiError(e)}`);
        break;
      }
    }

    setSelected(new Set());
    setApplyingMulti(false);
    setMultiProgress(null);
    setBaselineVersionCount(versions?.length ?? 0);
    setSuccessMsg(`${successCount} transformation${successCount !== 1 ? "s" : ""} applied in sequence — final version ready!`);
  };

  const selectedUnapplied = [...selected].filter((i) => !effectiveApplied.has(i));

  return (
    <div className="space-y-2">
      {successMsg && (
        <div className="text-xs text-green-700 bg-green-50 border border-green-200 rounded-lg px-3 py-2 flex justify-between">
          {successMsg}
          <button onClick={() => setSuccessMsg(null)} className="ml-2 text-green-500 hover:text-green-700">✕</button>
        </div>
      )}
      {errorMsg && (
        <div className="text-xs text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2 flex justify-between">
          {errorMsg}
          <button onClick={() => setErrorMsg(null)} className="ml-2 text-red-400 hover:text-red-600">✕</button>
        </div>
      )}

      {/* toolbar */}
      <div className="flex items-center gap-2 pb-1">
        <input
          type="checkbox"
          checked={unappliedIndices.length > 0 && unappliedIndices.every((i) => selected.has(i))}
          onChange={toggleSelectAll}
          className="rounded border-gray-300"
          title="Select all"
        />
        <span className="text-xs text-gray-500">
          {selected.size > 0 ? `${selected.size} selected` : "Select to bulk apply"}
        </span>
        {selectedUnapplied.length > 0 && (
          <button
            onClick={handleApplySelected}
            disabled={applyingMulti}
            className="ml-auto text-xs px-3 py-1.5 rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {applyingMulti ? multiProgress : `Apply selected (${selectedUnapplied.length})`}
          </button>
        )}
      </div>

      {rawActions.map((raw, idx) => {
        if (dismissed.has(idx)) return null;
        const isApplied = effectiveApplied.has(idx);
        const isSelected = selected.has(idx);
        return (
          <div
            key={idx}
            className={`flex items-start gap-3 border rounded-xl p-3 transition-colors ${
              isApplied
                ? "border-green-200 bg-green-50"
                : isSelected
                ? "border-blue-300 bg-blue-50"
                : "border-gray-200 bg-white"
            }`}
          >
            {!isApplied && (
              <input
                type="checkbox"
                checked={isSelected}
                onChange={() => toggleSelect(idx)}
                className="mt-0.5 rounded border-gray-300 shrink-0"
              />
            )}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <code className="text-xs bg-gray-100 px-1.5 py-0.5 rounded">{raw.action_type}</code>
                {raw.column && <code className="text-xs text-blue-600">{raw.column}</code>}
                {isApplied && <span className="text-xs text-green-600 font-medium">✓ Applied</span>}
                <span className={`text-xs ml-auto ${PRIORITY_COLORS[raw.priority] ?? "text-gray-400"}`}>
                  {raw.priority}
                </span>
              </div>
              <p className="text-xs text-gray-600">{raw.reason}</p>
            </div>
            <div className="flex gap-2 shrink-0">
              {!isApplied && (
                <button
                  onClick={() => handlePreview(raw, idx)}
                  disabled={preview.isPending || applyingMulti}
                  className="text-xs px-2.5 py-1.5 rounded-lg bg-blue-50 text-blue-600 hover:bg-blue-100 disabled:opacity-50"
                >
                  Preview
                </button>
              )}
              <button
                onClick={() => setDismissed((d) => { const next = new Set(d); next.add(idx); return next; })}
                className="text-xs px-2 py-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-50"
              >
                ✕
              </button>
            </div>
          </div>
        );
      })}

      {pending && (
        <CleaningConfirmModal
          action={pending.action}
          preview={pending.previewResult}
          isApplying={apply.isPending}
          onConfirm={handleSingleApply}
          onCancel={() => setPending(null)}
        />
      )}
    </div>
  );
}
