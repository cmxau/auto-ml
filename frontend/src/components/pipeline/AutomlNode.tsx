"use client";
import { Handle, Position, NodeProps } from "@xyflow/react";

export interface AutomlNodeData {
  node_type: string;
  node_name: string;
  config_json: Record<string, unknown>;
  [key: string]: unknown;
}

const NODE_COLORS: Record<string, string> = {
  input: "bg-blue-50 border-blue-300",
  cleaning: "bg-orange-50 border-orange-300",
  transformation: "bg-purple-50 border-purple-300",
  feature_engineering: "bg-indigo-50 border-indigo-300",
  split: "bg-gray-50 border-gray-300",
  train: "bg-green-50 border-green-300",
  evaluate: "bg-teal-50 border-teal-300",
  export: "bg-slate-50 border-slate-300",
};

export function AutomlNode({ data, selected }: NodeProps) {
  const nodeData = data as AutomlNodeData;
  const colorClass =
    NODE_COLORS[nodeData.node_type] ?? "bg-gray-50 border-gray-300";

  return (
    <div
      className={`border-2 rounded-xl px-4 py-3 min-w-[150px] text-center shadow-sm
        ${colorClass} ${selected ? "ring-2 ring-blue-500 ring-offset-1" : ""}`}
    >
      <Handle type="target" position={Position.Top} className="!bg-gray-400" />
      <p className="text-xs text-gray-500 mb-0.5">
        {nodeData.node_type.replace(/_/g, " ")}
      </p>
      <p className="text-sm font-medium text-gray-800 max-w-[120px] truncate mx-auto">
        {nodeData.node_name}
      </p>
      <Handle type="source" position={Position.Bottom} className="!bg-gray-400" />
    </div>
  );
}
