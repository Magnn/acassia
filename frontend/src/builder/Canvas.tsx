import { useCallback } from 'react';
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
  onNodesChange,
  onEdgesChange,
  onConnect,
  onAddNode,
}: CanvasProps) {
  const { screenToFlowPosition } = useReactFlow();

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
      className="h-full w-full bg-cigana-bg"
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
          color="#334155"
        />
        <MiniMap
          pannable
          zoomable
          maskColor="rgba(15, 23, 42, 0.7)"
          nodeColor={() => '#7c3aed'}
          nodeStrokeWidth={2}
        />
        <Controls position="bottom-right" showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
