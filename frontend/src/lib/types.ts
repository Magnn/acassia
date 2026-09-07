// Tipos espelhando o formato "meumisterio-flow" persistido em FlowBlueprint.body_json.
// Ver dashboard.html → extractFlowGraphFromDom / flowEdgeToPersist.

export type MeuMisterioNodeType =
  | 'trigger'
  | 'conteudo'
  | 'pergunta'
  | 'acao'
  | 'delay'
  | 'condicao'
  | 'gpt'
  | 'agente_ia'
  | 'voice_studio'
  | 'api'
  | 'integration'
  | 'ab_split'
  | 'motor_ref'
  | 'anotacao'
  | 'menu'
  | 'expediente'
  | 'notificar_atendente'
  | 'end'
  | (string & {}); // permite tipos novos sem quebrar build

export interface MeuMisterioNode {
  id: string;
  type: MeuMisterioNodeType;
  label: string;
  x: number;
  y: number;
  iconClass?: string;
  config: Record<string, unknown>;
}

export interface MeuMisterioEdge {
  id: string;
  from: string;
  to: string;
  sourceHandle?: string;
  targetHandle?: string;
  label?: string;
  /** deltas do ponto de controle Bezier — descartados na Fase 1 (React Flow tem Bezier nativo) */
  dc1x?: number;
  dc1y?: number;
  dc2x?: number;
  dc2y?: number;
}

export interface MeuMisterioGraph {
  nodes: MeuMisterioNode[];
  edges: MeuMisterioEdge[];
}

export interface MeuMisterioDocument {
  format?: 'meumisterio-flow';
  version?: number;
  title?: string;
  updatedAt?: string;
  graph?: MeuMisterioGraph;
  // campos legados/extra do dashboard.html (svgInner, nodesInnerHTML) são ignorados
}
