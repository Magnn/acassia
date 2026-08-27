import { type Edge, type Node } from '@xyflow/react';
import type { MeuMisterioDocument, MeuMisterioEdge, MeuMisterioNode } from './types';

export interface FlowNodeData extends Record<string, unknown> {
  label: string;
  meumisterioType: string;
  config: Record<string, unknown>;
  /** preenchido em runtime pelo lint — não é persistido. */
  lintLevel?: 'error' | 'warning';
  /** preenchido em runtime pelo simulador no nó corrente — não é persistido. */
  simActive?: boolean;
  /** callback para abrir o inspector — injetado em runtime pelo Builder. */
  onEdit?: () => void;
  /** callback para duplicar o nó — injetado em runtime pelo Builder. */
  onDuplicate?: () => void;
}

/** Converte um documento meumisterio-flow para os arrays que React Flow consome. */
export function documentToReactFlow(doc: MeuMisterioDocument): {
  nodes: Node<FlowNodeData>[];
  edges: Edge[];
} {
  const graph = doc.graph;
  if (!graph) return { nodes: [], edges: [] };

  const nodes: Node<FlowNodeData>[] = (graph.nodes ?? []).map((n) =>
    meumisterioNodeToReactFlow(n),
  );
  const edges: Edge[] = (graph.edges ?? []).map((e) => meumisterioEdgeToReactFlow(e));

  return { nodes, edges };
}

function meumisterioNodeToReactFlow(n: MeuMisterioNode): Node<FlowNodeData> {
  return {
    id: n.id,
    // Em Fase 1 usamos um único custom node "meumisterio" e diferenciamos por data.meumisterioType.
    // Em Fase 2+ migramos para um componente por tipo (ContentNode, ConditionNode, etc.).
    type: 'meumisterio',
    position: { x: n.x ?? 0, y: n.y ?? 0 },
    data: {
      label: n.label || n.type,
      meumisterioType: n.type,
      config: n.config ?? {},
    },
  };
}
function meumisterioEdgeToReactFlow(e: MeuMisterioEdge): Edge {
  return {
    id: e.id,
    source: e.from,
    target: e.to,
    sourceHandle: e.sourceHandle || null,
    targetHandle: e.targetHandle || null,
    type: 'default', // Smooth bezier curve
    label: e.label,
    animated: false,
    style: {
      strokeWidth: 3,
      stroke: '#7c3aed',
    },
  };
}
