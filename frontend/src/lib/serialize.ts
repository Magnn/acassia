import type { Edge, Node } from '@xyflow/react';
import type { FlowNodeData } from './adapt';
import type { MeuMisterioDocument, MeuMisterioEdge, MeuMisterioNode } from './types';

/**
 * Converte estado React Flow de volta para o documento meumisterio-flow persistido.
 * Mantém o título e versão do documento original.
 */
export function reactFlowToDocument(
  base: MeuMisterioDocument,
  nodes: Node<FlowNodeData>[],
  edges: Edge[],
): MeuMisterioDocument {
  return {
    format: 'meumisterio-flow',
    version: base.version ?? 1,
    title: base.title,
    updatedAt: new Date().toISOString(),
    graph: {
      nodes: nodes.map(reactFlowNodeToMeuMisterio),
      edges: edges.map(reactFlowEdgeToMeuMisterio),
    },
  };
}

function reactFlowNodeToMeuMisterio(n: Node<FlowNodeData>): MeuMisterioNode {
  return {
    id: n.id,
    type: n.data.meumisterioType,
    label: n.data.label,
    x: Math.round(n.position.x),
    y: Math.round(n.position.y),
    config: n.data.config ?? {},
  };
}

function reactFlowEdgeToMeuMisterio(e: Edge): MeuMisterioEdge {
  const out: MeuMisterioEdge = { id: e.id, from: e.source, to: e.target };
  if (typeof e.label === 'string' && e.label.trim()) out.label = e.label;
  return out;
}

let _idCounter = 0;
/** ID curto e único para novos nodes / edges criados na sessão. */
export function newId(prefix: string): string {
  _idCounter += 1;
  return `${prefix}-${Date.now().toString(36)}-${_idCounter.toString(36)}`;
}
