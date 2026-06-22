"use client";
import type { PreviewResult, CleaningAction } from "@/lib/api/cleaning";

interface Props {
  action: CleaningAction;
  preview: PreviewResult;
  isApplying: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function CleaningConfirmModal({
  action,
  preview,
  isApplying,
  onConfirm,
  onCancel,
}: Props) {
  const rowDelta = preview.rows_after - preview.rows_before;
  const colDelta = preview.columns_after - preview.columns_before;

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg p-6">
        <h2 className="text-base font-semibold text-gray-900 mb-1">{action.title}</h2>
        {action.description && (
          <p className="text-sm text-gray-500 mb-4">{action.description}</p>
        )}

        <div className="grid grid-cols-2 gap-3 mb-5">
          <Stat label="Rows before" value={preview.rows_before.toLocaleString()} />
          <Stat
            label="Rows after"
            value={preview.rows_after.toLocaleString()}
            delta={rowDelta}
          />
          <Stat label="Columns before" value={String(preview.columns_before)} />
          <Stat
            label="Columns after"
            value={String(preview.columns_after)}
            delta={colDelta}
          />
        </div>

        {preview.columns_removed.length > 0 && (
          <p className="text-xs text-red-600 mb-2">
            Removing columns: {preview.columns_removed.join(", ")}
          </p>
        )}
        {preview.columns_added.length > 0 && (
          <p className="text-xs text-green-600 mb-2">
            Adding columns: {preview.columns_added.join(", ")}
          </p>
        )}

        {preview.sample_rows.length > 0 && (
          <div className="mb-4 overflow-auto max-h-40 border border-gray-100 rounded-lg">
            <table className="text-xs w-full">
              <thead className="bg-gray-50">
                <tr>
                  {Object.keys(preview.sample_rows[0]).map((k) => (
                    <th key={k} className="px-2 py-1 text-left text-gray-500 font-medium">
                      {k}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {preview.sample_rows.map((row, i) => (
                  <tr key={i} className="border-t border-gray-100">
                    {Object.values(row).map((v, j) => (
                      <td key={j} className="px-2 py-1 text-gray-700">
                        {v == null ? <span className="text-gray-300">null</span> : String(v)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="flex justify-end gap-3">
          <button
            onClick={onCancel}
            className="text-sm px-4 py-2 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={isApplying}
            className="text-sm px-4 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {isApplying ? "Applying…" : "Apply transformation"}
          </button>
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value, delta }: { label: string; value: string; delta?: number }) {
  return (
    <div className="bg-gray-50 rounded-lg p-3">
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className="text-base font-semibold text-gray-900">
        {value}
        {delta != null && delta !== 0 && (
          <span className={`ml-1.5 text-xs font-medium ${delta < 0 ? "text-red-500" : "text-green-500"}`}>
            ({delta > 0 ? "+" : ""}{delta})
          </span>
        )}
      </p>
    </div>
  );
}
