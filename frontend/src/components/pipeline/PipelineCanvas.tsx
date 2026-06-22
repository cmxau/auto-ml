"use client";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ReactFlow,
  useNodesState,
  useEdgesState,
  addEdge,
  Controls,
  Background,
  MiniMap,
  ReactFlowProvider,
  type Connection,
  type Edge,
  type Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import { AutomlNode, type AutomlNodeData } from "./AutomlNode";
import { NodePalette } from "./NodePalette";
import { NodeInspector } from "./NodeInspector";
import { useSavePipeline, useValidatePipeline } from "@/lib/hooks/usePipeline";
import type { PipelineRecord } from "@/lib/api/pipelines";

const NODE_TYPES = { automlNode: AutomlNode };

interface Props {
  pipeline: PipelineRecord;
  projectId: string;
}

const DEFAULT_CONFIG: Record<string, Record<string, string>> = {
  input: { dataset_version_id: "" },
  split: { test_size: "0.2" },
  train: { dataset_version_id: "", model_type: "random_forest", task_type: "classification", target_column: "" },
};

function PipelineCanvasInner({ pipeline, projectId }: Props) {
  const save = useSavePipeline(pipeline.id);
  const validate = useValidatePipeline(pipeline.id);
  const [validationResult, setValidationResult] = useState<{
    valid: boolean;
    errors: string[];
  } | null>(null);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);

  const initialNodes: Node[] = useMemo(
    () =>
      pipeline.nodes.map((n) => ({
        id: n.id,
        type: "automlNode",
        position: { x: n.position_x ?? 0, y: n.position_y ?? 0 },
        data: {
          node_type: n.node_type,
          node_name: n.node_name,
          config_json: n.config_json,
        } as AutomlNodeData,
      })),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [pipeline.id]
  );

  const initialEdges: Edge[] = useMemo(
    () =>
      pipeline.edges.map((e) => ({
        id: e.id,
        source: e.source_node_id,
        target: e.target_node_id,
      })),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [pipeline.id]
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  useEffect(() => {
    setNodes(initialNodes);
    setEdges(initialEdges);
  }, [pipeline.id, setNodes, setEdges]);

  const onConnect = useCallback(
    (connection: Connection) => setEdges((eds) => addEdge(connection, eds)),
    [setEdges]
  );

  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => setSelectedNode(node),
    []
  );

  const onPaneClick = useCallback(() => setSelectedNode(null), []);

  const handleAddNode = (nodeType: string) => {
    const newNode: Node = {
      id: Math.random().toString(36).slice(2) + Date.now().toString(36),
      type: "automlNode",
      position: { x: 180 + Math.random() * 60, y: 80 + nodes.length * 130 },
      data: {
        node_type: nodeType,
        node_name: nodeType.replace(/_/g, " "),
        config_json: DEFAULT_CONFIG[nodeType] ? { ...DEFAULT_CONFIG[nodeType] } : {},
      } as AutomlNodeData,
    };
    setNodes((nds) => [...nds, newNode]);
    setValidationResult(null);
  };

  const handleNodeDataChange = (nodeId: string, data: AutomlNodeData) => {
    setNodes((nds) =>
      nds.map((n) => (n.id === nodeId ? { ...n, data } : n))
    );
    setSelectedNode((prev) =>
      prev?.id === nodeId ? { ...prev, data } : prev
    );
  };

  const handleSave = async () => {
    const saveNodes = nodes.map((n) => ({
      id: n.id,
      node_type: (n.data as AutomlNodeData).node_type,
      node_name: (n.data as AutomlNodeData).node_name,
      config_json: (n.data as AutomlNodeData).config_json ?? {},
      position_x: n.position.x,
      position_y: n.position.y,
    }));
    const saveEdges = edges.map((e) => ({
      source_node_id: e.source,
      target_node_id: e.target,
    }));
    try {
      await save.mutateAsync({ nodes: saveNodes, edges: saveEdges });
    } catch {
      alert("Save failed. Please try again.");
    }
  };

  const handleValidate = async () => {
    try {
      const result = await validate.mutateAsync();
      setValidationResult(result);
    } catch {
      alert("Validation failed.");
    }
  };

  return (
    <div className="flex h-full">
      <NodePalette onAddNode={handleAddNode} />

      <div className="flex-1 relative">
        {/* Toolbar */}
        <div className="absolute top-3 right-3 z-10 flex gap-2">
          <button
            onClick={handleValidate}
            disabled={validate.isPending}
            className="text-xs px-3 py-1.5 bg-white border border-gray-200 rounded-lg
              shadow-sm hover:bg-gray-50 disabled:opacity-50"
          >
            {validate.isPending ? "Validating…" : "Validate"}
          </button>
          <button
            onClick={handleSave}
            disabled={save.isPending}
            className="text-xs px-3 py-1.5 bg-blue-600 text-white rounded-lg
              shadow-sm hover:bg-blue-700 disabled:opacity-50"
          >
            {save.isPending ? "Saving…" : "Save pipeline"}
          </button>
        </div>

        {/* Validation badge */}
        {validationResult && (
          <div
            className={`absolute top-12 right-3 z-10 text-xs px-3 py-2 rounded-lg
              shadow-sm max-w-xs
              ${
                validationResult.valid
                  ? "bg-green-50 text-green-700 border border-green-200"
                  : "bg-red-50 text-red-700 border border-red-200"
              }`}
          >
            {validationResult.valid
              ? "✓ Valid DAG — ready to run"
              : validationResult.errors.join(" • ")}
          </div>
        )}

        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onNodeClick={onNodeClick}
          onPaneClick={onPaneClick}
          nodeTypes={NODE_TYPES}
          fitView
          deleteKeyCode="Backspace"
        >
          <Controls />
          <Background />
          <MiniMap />
        </ReactFlow>
      </div>

      <NodeInspector node={selectedNode} onChange={handleNodeDataChange} projectId={projectId} />
    </div>
  );
}

export function PipelineCanvas({ pipeline, projectId }: Props) {
  return (
    <ReactFlowProvider>
      <PipelineCanvasInner pipeline={pipeline} projectId={projectId} />
    </ReactFlowProvider>
  );
}
