"use client";
import { useState } from "react";
import type { CleaningAction, PreviewResult, TranslatedAction } from "@/lib/api/cleaning";
import { useTranslateCommand, usePreviewAction, useApplyAction } from "@/lib/hooks/useCleaning";
import { useDatasetVersions, useWaitForNewVersion } from "@/lib/hooks/useDatasets";
import { CleaningConfirmModal } from "./CleaningConfirmModal";
import { extractApiError } from "@/lib/api/client";

interface Props {
  datasetId: string;
  datasetVersionId: string | null;
}

export function CleaningCommandBox({ datasetId, datasetVersionId }: Props) {
  const [command, setCommand] = useState("");
  const [translated, setTranslated] = useState<TranslatedAction | null>(null);
  const [pending, setPending] = useState<{
    action: CleaningAction;
    previewResult: PreviewResult;
  } | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [baselineVersionCount, setBaselineVersionCount] = useState<number | null>(null);

  const translate = useTranslateCommand(datasetId);
  const preview = usePreviewAction(datasetVersionId);
  const apply = useApplyAction(datasetId, datasetVersionId);
  const { data: versions } = useDatasetVersions(datasetId);

  useWaitForNewVersion(datasetId, baselineVersionCount, () => {
    setSuccessMsg("New dataset version is ready!");
    setBaselineVersionCount(null);
  });

  const handleTranslate = async () => {
    if (!command.trim()) return;
    setTranslated(null);
    setErrorMsg(null);
    try {
      const result = await translate.mutateAsync(command.trim());
      setTranslated(result);
    } catch (e) {
      setErrorMsg(`Translation failed: ${extractApiError(e)}`);
    }
  };

  const handlePreview = async () => {
    if (!translated || !translated.action_type) return;
    setErrorMsg(null);
    const action: CleaningAction = {
      action_type: translated.action_type,
      parameters: translated.parameters,
      title: translated.title,
      description: translated.description,
      suggested_by: "user",
    };
    try {
      const result = await preview.mutateAsync(action);
      setPending({ action, previewResult: result });
    } catch (e) {
      setErrorMsg(`Preview failed: ${extractApiError(e)}`);
    }
  };

  const handleApply = async () => {
    if (!pending) return;
    setErrorMsg(null);
    try {
      const currentCount = versions?.length ?? 0;
      await apply.mutateAsync(pending.action);
      setPending(null);
      setTranslated(null);
      setCommand("");
      setBaselineVersionCount(currentCount);
      setSuccessMsg("Transformation queued — waiting for new version…");
    } catch (e) {
      setErrorMsg(`Apply failed: ${extractApiError(e)}`);
    }
  };

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4">
      <h3 className="text-sm font-semibold text-gray-800 mb-3">Clean with a command</h3>
      {successMsg && (
        <div className="mb-3 text-xs text-green-700 bg-green-50 border border-green-200 rounded-lg px-3 py-2 flex justify-between">
          {successMsg}
          <button onClick={() => setSuccessMsg(null)} className="ml-2 text-green-500 hover:text-green-700">✕</button>
        </div>
      )}
      {errorMsg && (
        <div className="mb-3 text-xs text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2 flex justify-between">
          {errorMsg}
          <button onClick={() => setErrorMsg(null)} className="ml-2 text-red-400 hover:text-red-600">✕</button>
        </div>
      )}

      <div className="flex gap-2 mb-3">
        <input
          type="text"
          value={command}
          onChange={(e) => setCommand(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleTranslate()}
          placeholder='e.g. "Remove rows where age is less than 18"'
          className="flex-1 text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-300"
        />
        <button
          onClick={handleTranslate}
          disabled={translate.isPending || !command.trim()}
          className="text-sm px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 shrink-0"
        >
          {translate.isPending ? "Thinking…" : "Translate"}
        </button>
      </div>

      {translated && (
        <div className="border border-gray-100 rounded-xl p-3 bg-gray-50">
          {translated.action_type ? (
            <>
              <div className="flex items-center gap-2 mb-2">
                <code className="text-xs bg-white border border-gray-200 px-2 py-0.5 rounded">
                  {translated.action_type}
                </code>
                <span className="text-xs text-gray-500">{translated.title}</span>
                <span className="text-xs text-gray-400 ml-auto">
                  {Math.round(translated.confidence * 100)}% confidence
                </span>
              </div>
              <p className="text-xs text-gray-600 mb-2">{translated.description}</p>
              {translated.warnings.length > 0 && (
                <p className="text-xs text-yellow-600 mb-2">
                  ⚠ {translated.warnings.join(" ")}
                </p>
              )}
              <button
                onClick={handlePreview}
                disabled={preview.isPending}
                className="text-xs px-3 py-1.5 bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100 disabled:opacity-50"
              >
                {preview.isPending ? "Loading preview…" : "Preview transformation"}
              </button>
            </>
          ) : (
            <p className="text-sm text-red-500">
              Could not interpret that command.{" "}
              {translated.warnings.length > 0 && translated.warnings[0]}
            </p>
          )}
        </div>
      )}

      {pending && (
        <CleaningConfirmModal
          action={pending.action}
          preview={pending.previewResult}
          isApplying={apply.isPending}
          onConfirm={handleApply}
          onCancel={() => setPending(null)}
        />
      )}
    </div>
  );
}
