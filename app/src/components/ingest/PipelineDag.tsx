/**
 * PipelineDag — horizontal React Flow DAG strip driven by server topology.
 *
 * Design choices:
 * - Manual x-layout: x = index * NODE_SLOT (no dagre dep)
 * - Group label strips rendered as non-interactive React Flow nodes above stage nodes
 * - Static viewport: fitView, no drag/zoom/connect
 * - Nodes and edges memoized to prevent layout thrash on 2s poll ticks
 * - Attribution retained (required for React Flow free tier)
 */
import React, { useMemo, useCallback } from 'react';
import {
  ReactFlow,
  Handle,
  Position,
  type Node,
  type Edge,
  type NodeProps,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { CheckCircle2, XCircle, Loader2, Circle } from 'lucide-react';
import type { PipelineTopology, MapProgress } from '@/lib/api';
import { type StageView, type StageStatus } from './stageState';

// ── Layout constants ──────────────────────────────────────────────────────────
const NODE_WIDTH = 140;
const NODE_HEIGHT = 88; // base height; fan-out nodes taller
const FAN_OUT_NODE_HEIGHT = 108;
const H_GAP = 48; // horizontal gap between nodes
const NODE_SLOT = NODE_WIDTH + H_GAP; // 188 px per slot
const GROUP_LABEL_H = 24; // height of group label strip
const NODE_Y = GROUP_LABEL_H + 6; // y position of stage nodes

// ── Data shapes passed through React Flow node data ───────────────────────────
type StageNodeData = {
  stageView: StageView;
  fanOut: boolean;
  mapProgress?: MapProgress | null;
};

type GroupLabelNodeData = {
  groupName: string;
};

// ── Status icon helper ────────────────────────────────────────────────────────
function StatusIcon({ status }: { status: StageStatus }) {
  if (status === 'done')
    return <CheckCircle2 className="h-4 w-4 shrink-0 text-green-400" />;
  if (status === 'running')
    return <Loader2 className="h-4 w-4 shrink-0 animate-spin text-amber-400" />;
  if (status === 'failed')
    return <XCircle className="h-4 w-4 shrink-0 text-red-400" />;
  return <Circle className="h-4 w-4 shrink-0 text-neutral-600" />;
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

/** Pick the first short numeric metric to display as a badge. */
function pickKeyMetric(metrics?: Record<string, unknown>): string | null {
  if (!metrics) return null;
  const preferred = ['chunk_count', 'entity_count', 'page_count', 'link_count'];
  for (const k of preferred) {
    if (typeof metrics[k] === 'number') return `${k.replace(/_/g, ' ')}: ${metrics[k]}`;
  }
  // Fall back to first numeric value
  for (const [k, v] of Object.entries(metrics)) {
    if (typeof v === 'number') return `${k.replace(/_/g, ' ')}: ${v}`;
  }
  return null;
}

// ── Custom nodes ──────────────────────────────────────────────────────────────

const StageNodeComponent = React.memo(function StageNodeComponent({
  data,
}: NodeProps<Node<StageNodeData>>) {
  const { stageView: sv, fanOut, mapProgress } = data;

  const borderClass =
    sv.status === 'done'
      ? 'border-green-700/40 bg-green-950/30'
      : sv.status === 'running'
        ? 'border-amber-600/50 bg-amber-950/30'
        : sv.status === 'failed'
          ? 'border-red-700/40 bg-red-950/30'
          : 'border-neutral-700/40 bg-neutral-900/30';

  const keyMetric = sv.status === 'done' ? pickKeyMetric(sv.metrics) : null;

  return (
    <div
      className={`relative flex flex-col gap-1 rounded-md border px-2.5 py-2 text-left transition-colors hover:brightness-110 ${borderClass}`}
      style={{ width: NODE_WIDTH, minHeight: NODE_HEIGHT }}
    >
      <Handle
        type="target"
        position={Position.Left}
        style={{ opacity: 0, pointerEvents: 'none' }}
      />

      {/* Header row: label + icon */}
      <div className="flex items-start justify-between gap-1">
        <span
          className="text-[11px] font-medium leading-tight text-neutral-200"
          style={{ maxWidth: NODE_WIDTH - 32 }}
        >
          {sv.label}
        </span>
        <StatusIcon status={sv.status} />
      </div>

      {/* Duration badge */}
      {sv.durationMs !== undefined && (
        <span className="text-[10px] tabular-nums text-neutral-500">
          {formatDuration(sv.durationMs)}
        </span>
      )}

      {/* Key metric */}
      {keyMetric && (
        <span className="text-[10px] text-neutral-400">{keyMetric}</span>
      )}

      {/* Failure message */}
      {sv.status === 'failed' && sv.failureMessage && (
        <span className="line-clamp-2 text-[10px] text-red-400">{sv.failureMessage}</span>
      )}

      {/* Fan-out progress bar */}
      {fanOut && mapProgress && mapProgress.total > 0 && (
        <div className="mt-1">
          <div className="mb-0.5 flex justify-between text-[9px] tabular-nums text-neutral-500">
            <span>
              {mapProgress.done}/{mapProgress.total}
            </span>
            {mapProgress.failed > 0 && (
              <span className="text-red-400">{mapProgress.failed} failed</span>
            )}
          </div>
          <div className="h-1 w-full overflow-hidden rounded-full bg-neutral-700">
            <div
              className="h-full rounded-full bg-amber-500 transition-all"
              style={{ width: `${(mapProgress.done / mapProgress.total) * 100}%` }}
            />
          </div>
        </div>
      )}

      <Handle
        type="source"
        position={Position.Right}
        style={{ opacity: 0, pointerEvents: 'none' }}
      />
    </div>
  );
});

const GroupLabelNodeComponent = React.memo(function GroupLabelNodeComponent({
  data,
}: NodeProps<Node<GroupLabelNodeData>>) {
  return (
    <div className="flex h-full items-center px-2">
      <span className="text-[10px] font-semibold uppercase tracking-widest text-neutral-600">
        {data.groupName}
      </span>
    </div>
  );
});

// nodeTypes must be defined at module level to stay stable across renders.
// Double-cast required because our typed node components have stricter data shapes
// than the base NodeProps<Node> generic used by React Flow's nodeTypes registry.
const nodeTypes = {
  stage: StageNodeComponent as unknown as React.ComponentType<NodeProps>,
  groupLabel: GroupLabelNodeComponent as unknown as React.ComponentType<NodeProps>,
};

// ── Main component ────────────────────────────────────────────────────────────

interface PipelineDagProps {
  topology: PipelineTopology;
  stages: StageView[];
  mapProgress?: MapProgress | null;
  onStageClick: (stage: StageView) => void;
}

export default function PipelineDag({
  topology,
  stages,
  mapProgress,
  onStageClick,
}: PipelineDagProps) {
  // Build nodes + edges, memoized on topology + stage state changes
  const { nodes, edges } = useMemo(() => {
    const stageMap = new Map(stages.map((s) => [s.key, s]));

    const builtNodes: Node[] = [];
    const builtEdges: Edge[] = [];

    // Group label nodes
    const intakeStages = topology.stages.filter((s) => s.group === 'intake');
    const cognifyStages = topology.stages.filter((s) => s.group === 'cognify');

    if (intakeStages.length > 0) {
      const firstIdx = intakeStages[0].index;
      const lastIdx = intakeStages[intakeStages.length - 1].index;
      const x = firstIdx * NODE_SLOT;
      const width = (lastIdx - firstIdx) * NODE_SLOT + NODE_WIDTH;
      builtNodes.push({
        id: 'g-intake',
        type: 'groupLabel',
        position: { x, y: 0 },
        data: { groupName: 'intake' } satisfies GroupLabelNodeData,
        selectable: false,
        focusable: false,
        draggable: false,
        style: { width, height: GROUP_LABEL_H, pointerEvents: 'none' },
      });
    }

    if (cognifyStages.length > 0) {
      const firstIdx = cognifyStages[0].index;
      const lastIdx = cognifyStages[cognifyStages.length - 1].index;
      const x = firstIdx * NODE_SLOT;
      const width = (lastIdx - firstIdx) * NODE_SLOT + NODE_WIDTH;
      builtNodes.push({
        id: 'g-cognify',
        type: 'groupLabel',
        position: { x, y: 0 },
        data: { groupName: 'cognify' } satisfies GroupLabelNodeData,
        selectable: false,
        focusable: false,
        draggable: false,
        style: { width, height: GROUP_LABEL_H, pointerEvents: 'none' },
      });
    }

    // Stage nodes
    for (const stage of topology.stages) {
      const sv = stageMap.get(stage.key) ?? {
        key: stage.key,
        label: stage.label,
        status: 'pending' as const,
      };
      const isFanOut = stage.fan_out;
      builtNodes.push({
        id: `stage-${stage.index}`,
        type: 'stage',
        position: { x: stage.index * NODE_SLOT, y: NODE_Y },
        data: {
          stageView: sv,
          fanOut: isFanOut,
          mapProgress: isFanOut ? mapProgress : undefined,
        } satisfies StageNodeData,
        draggable: false,
        selectable: true,
        style: {
          width: NODE_WIDTH,
          height: isFanOut && mapProgress ? FAN_OUT_NODE_HEIGHT : NODE_HEIGHT,
        },
      });
    }

    // Edges: linear chain
    for (let i = 1; i < topology.stages.length; i++) {
      builtEdges.push({
        id: `e-${i - 1}-${i}`,
        source: `stage-${i - 1}`,
        target: `stage-${i}`,
        type: 'smoothstep',
        style: { stroke: '#404040', strokeWidth: 1.5 },
        animated: stages[i - 1]?.status === 'running' || stages[i]?.status === 'running',
      });
    }

    return { nodes: builtNodes, edges: builtEdges };
  }, [topology, stages, mapProgress]);

  const handleNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      if (node.type !== 'stage') return;
      const sv = (node.data as StageNodeData).stageView;
      onStageClick(sv);
    },
    [onStageClick],
  );

  return (
    <div
      className="relative w-full overflow-hidden rounded-lg border border-neutral-800"
      style={{ height: 210 }}
    >
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodeClick={handleNodeClick}
        fitView
        fitViewOptions={{ padding: 0.12 }}
        nodesDraggable={false}
        nodesConnectable={false}
        zoomOnScroll={false}
        zoomOnPinch={false}
        panOnDrag={false}
        panOnScroll={false}
        elementsSelectable={true}
        deleteKeyCode={null}
        colorMode="dark"
        proOptions={{ hideAttribution: false }}
        className="!bg-neutral-950"
      />
    </div>
  );
}
