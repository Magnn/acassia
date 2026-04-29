import { useMemo } from 'react';
import {
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  type Edge,
  type Node,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import AcassiaNode from './AcassiaNode';
import type { AcassiaDocument } from '../lib/types';
import { documentToReactFlow, type FlowNodeData } from '../lib/adapt';

interface CanvasProps {
  doc: AcassiaDocument;
}

const nodeTypes = { acassia: AcassiaNode } as const;

export default function Canvas({ doc }: CanvasProps) {
  const { nodes, edges } = useMemo(() => documentToReactFlow(doc), [doc]);

  return (
    <ReactFlowProvider>
      <CanvasInner nodes={nodes} edges={edges} />
    </ReactFlowProvider>
  );
}

function CanvasInner({
  nodes,
  edges,
}: {
  nodes: Node<FlowNodeData>[];
  edges: Edge[];
}) {
  return (
    <div className="h-full w-full bg-cigana-bg">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        // Fase 1 = read-only. Fase 2 ativa edição.
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable
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
