import type { Edge, Node } from '@xyflow/react';
import type { AcassiaDocument, AcassiaEdge, AcassiaNode } from './types';

export interface FlowNodeData extends Record<string, unknown> {
  label: string;
  acassiaType: string;
  config: Record<string, unknown>;
  /** preenchido em runtime pelo lint — não é persistido. */
  lintLevel?: 'error' | 'warning';
}

/** Converte um documento acassia-flow para os arrays que React Flow consome. */
export function documentToReactFlow(doc: AcassiaDocument): {
  nodes: Node<FlowNodeData>[];
  edges: Edge[];
} {
  const graph = doc.graph;
  if (!graph) return { nodes: [], edges: [] };

  const nodes: Node<FlowNodeData>[] = (graph.nodes ?? []).map((n) =>
    acassiaNodeToReactFlow(n),
  );
  const edges: Edge[] = (graph.edges ?? []).map((e) => acassiaEdgeToReactFlow(e));

  return { nodes, edges };
}

function acassiaNodeToReactFlow(n: AcassiaNode): Node<FlowNodeData> {
  return {
    id: n.id,
    // Em Fase 1 usamos um único custom node "acassia" e diferenciamos por data.acassiaType.
    // Em Fase 2+ migramos para um componente por tipo (ContentNode, ConditionNode, etc.).
    type: 'acassia',
    position: { x: n.x ?? 0, y: n.y ?? 0 },
    data: {
      label: n.label || n.type,
      acassiaType: n.type,
      config: n.config ?? {},
    },
  };
}

function acassiaEdgeToReactFlow(e: AcassiaEdge): Edge {
  return {
    id: e.id,
    source: e.from,
    target: e.to,
    type: 'default', // Bezier nativo do React Flow
    label: e.label,
    animated: false,
  };
}
