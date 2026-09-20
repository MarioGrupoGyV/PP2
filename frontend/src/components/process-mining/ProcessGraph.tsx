import { useMemo } from "react";
import dagre from "@dagrejs/dagre";
import {
  Background,
  Controls,
  Handle,
  MarkerType,
  MiniMap,
  Position,
  ReactFlow,
  type Edge,
  type EdgeMouseHandler,
  type Node,
  type NodeMouseHandler,
  type NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import type {
  DfgResponse,
  TransitionStatistic,
} from "../../types/processMining";

const NODE_WIDTH = 190;
const NODE_HEIGHT = 82;

type ActivityNodeData = {
  activity: string;
  frequency: number;
  caseFrequency: number;
};

type ActivityFlowNode = Node<ActivityNodeData, "activity">;
type TransitionEdgeData = {
  transition: TransitionStatistic;
};
type TransitionFlowEdge = Edge<TransitionEdgeData>;

function ActivityNode({ data, selected }: NodeProps<ActivityFlowNode>) {
  return (
    <div
      className={`min-w-[190px] rounded-xl border-2 bg-white px-4 py-3 shadow-md transition ${
        selected
          ? "border-teal-500 shadow-teal-200"
          : "border-slate-200 shadow-slate-200/70"
      }`}
    >
      <Handle type="target" position={Position.Left} className="!bg-slate-400" />
      <p className="truncate text-sm font-bold text-slate-900">{data.activity}</p>
      <p className="mt-1 text-xs font-medium text-slate-500">
        {data.frequency.toLocaleString("es-PE")} eventos ·{" "}
        {data.caseFrequency.toLocaleString("es-PE")} casos
      </p>
      <Handle type="source" position={Position.Right} className="!bg-teal-600" />
    </div>
  );
}

const nodeTypes = { activity: ActivityNode };

function layoutGraph(
  dfg: DfgResponse,
  transitions: TransitionStatistic[],
): { nodes: ActivityFlowNode[]; edges: TransitionFlowEdge[] } {
  const graph = new dagre.graphlib.Graph().setDefaultEdgeLabel(() => ({}));
  graph.setGraph({ rankdir: "LR", ranksep: 95, nodesep: 55, marginx: 35, marginy: 35 });

  const idByActivity = new Map<string, string>();
  dfg.nodes.forEach((node, index) => {
    const id = `activity-${index}`;
    idByActivity.set(node.activity, id);
    graph.setNode(id, { width: NODE_WIDTH, height: NODE_HEIGHT });
  });
  dfg.edges.forEach((edge) => {
    const source = idByActivity.get(edge.source);
    const target = idByActivity.get(edge.target);
    if (source && target) graph.setEdge(source, target);
  });
  dagre.layout(graph);

  const transitionByKey = new Map(
    transitions.map((item) => [`${item.source}\u0000${item.target}`, item]),
  );
  const nodes: ActivityFlowNode[] = dfg.nodes.map((node, index) => {
    const id = `activity-${index}`;
    const position = graph.node(id);
    return {
      id,
      type: "activity",
      position: {
        x: position.x - NODE_WIDTH / 2,
        y: position.y - NODE_HEIGHT / 2,
      },
      data: {
        activity: node.activity,
        frequency: node.frequency,
        caseFrequency: node.case_frequency,
      },
    };
  });
  const edges: TransitionFlowEdge[] = dfg.edges.flatMap((edge, index) => {
    const source = idByActivity.get(edge.source);
    const target = idByActivity.get(edge.target);
    const transition = transitionByKey.get(`${edge.source}\u0000${edge.target}`);
    if (!source || !target || !transition) return [];
    return [
      {
        id: `transition-${index}`,
        source,
        target,
        type: "smoothstep",
        label: edge.frequency.toLocaleString("es-PE"),
        labelBgPadding: [7, 4],
        labelBgBorderRadius: 6,
        labelBgStyle: { fill: "#ffffff", fillOpacity: 0.94 },
        labelStyle: { fill: "#334155", fontWeight: 700, fontSize: 11 },
        markerEnd: { type: MarkerType.ArrowClosed, color: "#0f766e" },
        style: { stroke: "#0f766e", strokeWidth: 1.8 },
        data: { transition },
      },
    ];
  });
  return { nodes, edges };
}

interface ProcessGraphProps {
  dfg: DfgResponse;
  transitions: TransitionStatistic[];
  onSelectActivity: (activity: string) => void;
  onSelectTransition: (transition: TransitionStatistic) => void;
}

export function ProcessGraph({
  dfg,
  transitions,
  onSelectActivity,
  onSelectTransition,
}: ProcessGraphProps) {
  const elements = useMemo(
    () => layoutGraph(dfg, transitions),
    [dfg, transitions],
  );
  const handleNodeClick: NodeMouseHandler<ActivityFlowNode> = (_, node) => {
    onSelectActivity(node.data.activity);
  };
  const handleEdgeClick: EdgeMouseHandler<TransitionFlowEdge> = (_, edge) => {
    if (edge.data?.transition) onSelectTransition(edge.data.transition);
  };

  return (
    <div className="h-[540px] overflow-hidden rounded-2xl border border-slate-200 bg-slate-50">
      <ReactFlow<ActivityFlowNode, TransitionFlowEdge>
        nodes={elements.nodes}
        edges={elements.edges}
        nodeTypes={nodeTypes}
        onNodeClick={handleNodeClick}
        onEdgeClick={handleEdgeClick}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable
        fitView
        fitViewOptions={{ padding: 0.18, maxZoom: 1.25 }}
        minZoom={0.2}
        maxZoom={1.8}
      >
        <Background color="#cbd5e1" gap={22} size={1} />
        <MiniMap
          pannable
          zoomable
          nodeColor="#0f766e"
          maskColor="rgba(248, 250, 252, 0.72)"
        />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
