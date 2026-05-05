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
import MeuMisterioNode from './MeuMisterioNode';
import { DRAG_MIME } from './Palette';
import type { FlowNodeData } from '../lib/adapt';
import type { MeuMisterioNodeType } from '../lib/types';

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
    type: MeuMisterioNodeType,
    position: { x: number; y: number },
  ) => void;
}

const nodeTypes = { meumisterio: MeuMisterioNode } as const;

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

  // ── Conexão segura: rejeita self-loops, duplicatas e conexões heréticas ──
  const isValidConnection = useCallback(
    (conn: Connection) => {
      if (!conn.source || !conn.target) return false;
      // Self-loop
      if (conn.source === conn.target) return false;
      // Duplicata (mesma source+target já existe)
      if (edges.some((e) => e.source === conn.source && e.target === conn.target)) return false;
      // Não pode conectar a um trigger (só saída)
      const targetNode = nodes.find((n) => n.id === conn.target);
      if (targetNode?.data.meumisterioType === 'trigger') return false;
      // Nós de saída única (não-branching) já têm 1 edge de saída?
      const sourceNode = nodes.find((n) => n.id === conn.source);
      const branchingTypes = new Set(['condicao', 'ab_split', 'pergunta', 'divisao']);
      if (sourceNode && !branchingTypes.has(sourceNode.data.meumisterioType)) {
        const existingOut = edges.filter((e) => e.source === conn.source);
        if (existingOut.length >= 1) return false;
      }
      return true;
    },
    [nodes, edges],
  );

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
      const type = e.dataTransfer.getData(DRAG_MIME) as MeuMisterioNodeType;
      if (!type) return;
      e.preventDefault();
      const position = screenToFlowPosition({ x: e.clientX, y: e.clientY });
      onAddNode(type, position);
    },
    [screenToFlowPosition, onAddNode],
  );

  return (
    <div
      className="h-full w-full transition-colors duration-500"
      style={{ background: 'linear-gradient(180deg, #f8fafc 0%, #f1f5f9 50%, #eef2f7 100%)' }}
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
        isValidConnection={isValidConnection}
        proOptions={{ hideAttribution: true }}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={22}
          size={1}
          color="rgba(15, 23, 42, 0.06)"
        />
        <MiniMap
          pannable
          zoomable
          maskColor="var(--bg-primary)"
          nodeColor={() => 'var(--accent-amethyst)'}
          nodeStrokeWidth={2}
          className="bg-bg-surface border border-border rounded-xl shadow-lg !bottom-4 !right-4"
        />
        <Controls position="bottom-right" showInteractive={false} className="!bottom-4 !left-4 !flex-row !bg-bg-surface !border-border !shadow-lg" />
      </ReactFlow>
    </div>
  );
}
