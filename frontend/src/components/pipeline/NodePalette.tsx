"use client";

const NODE_TYPE_CONFIGS = [
  { type: "input", label: "Input Dataset" },
  { type: "cleaning", label: "Clean Data" },
  { type: "transformation", label: "Transform" },
  { type: "feature_engineering", label: "Feature Engineer" },
  { type: "split", label: "Train/Test Split" },
  { type: "train", label: "Train Model" },
  { type: "evaluate", label: "Evaluate" },
  { type: "export", label: "Export" },
] as const;

interface Props {
  onAddNode: (nodeType: string) => void;
}

export function NodePalette({ onAddNode }: Props) {
  return (
    <div className="w-48 border-r border-gray-200 bg-white p-3 flex flex-col gap-1.5 shrink-0 overflow-y-auto">
      <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
        Add Node
      </h3>
      {NODE_TYPE_CONFIGS.map(({ type, label }) => (
        <button
          key={type}
          onClick={() => onAddNode(type)}
          className="text-xs text-left px-3 py-2 rounded-lg border border-gray-200
            text-gray-700 hover:bg-blue-50 hover:border-blue-300 hover:text-blue-700
            transition-colors"
        >
          {label}
        </button>
      ))}
    </div>
  );
}
