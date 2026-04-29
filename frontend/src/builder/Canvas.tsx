import { useCallback, useEffect } from 'react';
import {
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  useReactFlow,
  type Connection,
  type Edge,
  type EdgeChange,
  type Node,
  type NodeChange,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import AcassiaNode from './AcassiaNode';
import { DRAG_MIME } from './Palette';
import type { FlowNodeData } from '../lib/adapt';
import type { AcassiaNodeType } from '../lib/types';

interface CanvasProps {
  nodes: Node<FlowNodeData>[];
  edges: Edge[];
  editable: boolean;
  /** quando muda, centra a viewport no nó indicado (botão "focar" no lint). */
  focusRequest?: { id: string; ts: number } | null;
  onNodesChange: (changes: NodeChange<Node<FlowNodeData>>[]) => void;
  onEdgesChange: (changes: EdgeChange[]) => void;
  onConnect: (conn: Connection) => void;
  onAddNode: (
    type: AcassiaNodeType,
    position: { x: number; y: number },
  ) => void;
}

const nodeTypes = { acassia: AcassiaNode } as const;

export default function Canvas(props: CanvasProps) {
  return (
    <ReactFlowProvider>
      <CanvasInner {...props} />
    </ReactFlowProvider>
  );
}

function CanvasInner({
  nodes,
  edges,
  editable,
  focusRequest,
  onNodesChange,
  onEdgesChange,
  onConnect,
  onAddNode,
}: CanvasProps) {
  const { screenToFlowPosition, setCenter } = useReactFlow();

  useEffect(() => {
    if (!focusRequest) return;
    const node = nodes.find((n) => n.id === focusRequest.id);
    if (!node) return;
    const cx = node.position.x + (node.measured?.width ?? 200) / 2;
    const cy = node.position.y + (node.measured?.height ?? 80) / 2;
    setCenter(cx, cy, { duration: 400, zoom: 1.1 });
    onNodesChange([{ type: 'select', id: focusRequest.id, selected: true }]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focusRequest]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    if (!e.dataTransfer.types.includes(DRAG_MIME)) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      const type = e.dataTransfer.getData(DRAG_MIME) as AcassiaNodeType;
      if (!type) return;
      e.preventDefault();
      const position = screenToFlowPosition({ x: e.clientX, y: e.clientY });
      onAddNode(type, position);
    },
    [screenToFlowPosition, onAddNode],
  );

  return (
    <div
      className="h-full w-full bg-gradient-to-br from-[#f8fafc] to-[#eef2f7]"
      onDragOver={editable ? handleDragOver : undefined}
      onDrop={editable ? handleDrop : undefined}
    >
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        fitView
        nodesDraggable={editable}
        nodesConnectable={editable}
        elementsSelectable
        deleteKeyCode={editable ? ['Delete', 'Backspace'] : null}
        proOptions={{ hideAttribution: true }}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={24}
          size={1}
          color="#cbd5e1"
        />
        <MiniMap
          pannable
          zoomable
          maskColor="rgba(248, 250, 252, 0.7)"
          nodeColor={() => '#7c3aed'}
          nodeStrokeWidth={2}
          className="bg-white border border-slate-200 rounded-lg shadow-sm"
        />
        <Controls position="bottom-right" showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
