"use client";
import type { Node } from "@xyflow/react";
import type { AutomlNodeData } from "./AutomlNode";
import { useDatasets, useDatasetVersions } from "@/lib/hooks/useDatasets";
import { useState } from "react";

interface Props {
  node: Node | null;
  onChange: (nodeId: string, data: AutomlNodeData) => void;
  projectId: string;
}

function InputNodeConfig({
  projectId,
  config,
  onConfigChange,
}: {
  projectId: string;
  config: Record<string, unknown>;
  onConfigChange: (key: string, value: string) => void;
}) {
  const [selectedDatasetId, setSelectedDatasetId] = useState("");
  const { data: datasets } = useDatasets(projectId);
  const { data: versions } = useDatasetVersions(selectedDatasetId);

  const sortedVersions = versions
    ? [...versions].sort((a, b) => b.version_number - a.version_number)
    : [];

  return (
    <div className="space-y-3">
      <div>
        <label className="text-xs text-gray-500 block mb-1">Dataset</label>
        <select
          value={selectedDatasetId}
          onChange={(e) => {
            setSelectedDatasetId(e.target.value);
            onConfigChange("dataset_version_id", "");
          }}
          className="w-full text-xs border border-gray-200 rounded-lg px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-300"
        >
          <option value="">Select dataset…</option>
          {datasets?.filter((d) => d.status === "ready").map((d) => (
            <option key={d.id} value={d.id}>{d.name}</option>
          ))}
        </select>
      </div>
      <div>
        <label className="text-xs text-gray-500 block mb-1">Version</label>
        <select
          value={String(config.dataset_version_id ?? "")}
          onChange={(e) => onConfigChange("dataset_version_id", e.target.value)}
          disabled={!selectedDatasetId}
          className="w-full text-xs border border-gray-200 rounded-lg px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-300 disabled:opacity-50"
        >
          <option value="">{selectedDatasetId ? "Select version…" : "Select dataset first"}</option>
          {sortedVersions.map((v) => (
            <option key={v.id} value={v.id}>
              v{v.version_number}{v.row_count != null ? ` · ${v.row_count.toLocaleString()} rows` : ""}
            </option>
          ))}
        </select>
      </div>
      {config.dataset_version_id && (
        <p className="text-xs text-green-600">✓ Version selected</p>
      )}
    </div>
  );
}

export function NodeInspector({ node, onChange, projectId }: Props) {
  if (!node) {
    return (
      <div className="w-56 border-l border-gray-200 bg-white p-4 shrink-0">
        <p className="text-xs text-gray-400 text-center mt-8">
          Select a node to edit properties.
        </p>
      </div>
    );
  }

  const data = node.data as AutomlNodeData;

  const handleConfigChange = (key: string, value: string) => {
    onChange(node.id, {
      ...data,
      config_json: { ...data.config_json, [key]: value },
    });
  };

  return (
    <div className="w-56 border-l border-gray-200 bg-white p-4 shrink-0 overflow-y-auto">
      <h3 className="text-sm font-semibold text-gray-800 mb-4">Node Properties</h3>

      <div className="mb-3">
        <label className="text-xs text-gray-500 block mb-1">Type</label>
        <p className="text-sm text-gray-700 capitalize">
          {data.node_type.replace(/_/g, " ")}
        </p>
      </div>

      <div className="mb-4">
        <label className="text-xs text-gray-500 block mb-1">Name</label>
        <input
          type="text"
          value={data.node_name}
          onChange={(e) => onChange(node.id, { ...data, node_name: e.target.value })}
          className="w-full text-sm border border-gray-200 rounded-lg px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-300"
        />
      </div>

      {data.node_type === "input" ? (
        <div>
          <label className="text-xs text-gray-500 block mb-2">Configuration</label>
          <InputNodeConfig
            projectId={projectId}
            config={data.config_json}
            onConfigChange={handleConfigChange}
          />
        </div>
      ) : Object.keys(data.config_json).length > 0 ? (
        <div>
          <label className="text-xs text-gray-500 block mb-2">Configuration</label>
          {Object.entries(data.config_json).map(([key, val]) => (
            <div key={key} className="mb-2">
              <label className="text-xs text-gray-400 block mb-0.5">{key.replace(/_/g, " ")}</label>
              <input
                type="text"
                value={String(val ?? "")}
                onChange={(e) => handleConfigChange(key, e.target.value)}
                className="w-full text-xs border border-gray-200 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-300"
              />
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}
