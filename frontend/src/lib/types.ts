// Tipos espelhando o formato "acassia-flow" persistido em FlowBlueprint.body_json.
// Ver dashboard.html → extractFlowGraphFromDom / flowEdgeToPersist.

export type AcassiaNodeType =
  | 'trigger'
  | 'conteudo'
  | 'delay'
  | 'condicao'
  | 'gpt'
  | 'api'
  | 'ab_split'
  | 'motor_ref'
  | 'anotacao'
  | 'end'
  | (string & {}); // permite tipos novos sem quebrar build

export interface AcassiaNode {
  id: string;
  type: AcassiaNodeType;
  label: string;
  x: number;
  y: number;
  iconClass?: string;
  config: Record<string, unknown>;
}

export interface AcassiaEdge {
  id: string;
  from: string;
  to: string;
  label?: string;
  /** deltas do ponto de controle Bezier — descartados na Fase 1 (React Flow tem Bezier nativo) */
  dc1x?: number;
  dc1y?: number;
  dc2x?: number;
  dc2y?: number;
}

export interface AcassiaGraph {
  nodes: AcassiaNode[];
  edges: AcassiaEdge[];
}

export interface AcassiaDocument {
  format?: 'acassia-flow';
  version?: number;
  title?: string;
  updatedAt?: string;
  graph?: AcassiaGraph;
  // campos legados/extra do dashboard.html (svgInner, nodesInnerHTML) são ignorados
}
