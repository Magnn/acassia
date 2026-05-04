import type { Edge, Node } from '@xyflow/react';
import type { FlowNodeData } from '../lib/adapt';

export type LintLevel = 'error' | 'warning';

export interface LintIssue {
  code: LintCode;
  level: LintLevel;
  nodeId?: string;
  edgeId?: string;
  message: string;
}

export type LintCode =
  | 'no_trigger'
  | 'multiple_triggers'
  | 'orphan_node'
  | 'unreachable'
  | 'dead_end'
  | 'condition_no_branches'
  | 'self_loop'
  | 'duplicate_edge'
  | 'empty_label';

export function lintGraph(
  nodes: Node<FlowNodeData>[],
  edges: Edge[],
): LintIssue[] {
  const issues: LintIssue[] = [];

  // Indexação rápida.
  const incoming = new Map<string, Edge[]>();
  const outgoing = new Map<string, Edge[]>();
  for (const e of edges) {
    if (!incoming.has(e.target)) incoming.set(e.target, []);
    if (!outgoing.has(e.source)) outgoing.set(e.source, []);
    incoming.get(e.target)!.push(e);
    outgoing.get(e.source)!.push(e);
  }

  // Triggers: zero ou múltiplos.
  const triggers = nodes.filter((n) => n.data.meumisterioType === 'trigger');
  if (triggers.length === 0) {
    issues.push({
      code: 'no_trigger',
      level: 'warning',
      message: 'Nenhum gatilho — o fluxo não tem ponto de entrada.',
    });
  } else if (triggers.length > 1) {
    issues.push({
      code: 'multiple_triggers',
      level: 'warning',
      message: `${triggers.length} gatilhos — geralmente um fluxo tem só um.`,
    });
  }

  // Self-loop e duplicate edge.
  const seen = new Set<string>();
  for (const e of edges) {
    if (e.source === e.target) {
      issues.push({
        code: 'self_loop',
        level: 'error',
        edgeId: e.id,
        nodeId: e.source,
        message: 'Aresta liga o nó a si mesmo.',
      });
    }
    const key = `${e.source}→${e.target}`;
    if (seen.has(key)) {
      issues.push({
        code: 'duplicate_edge',
        level: 'warning',
        edgeId: e.id,
        message: 'Aresta duplicada entre os mesmos nós.',
      });
    } else {
      seen.add(key);
    }
  }

  // Reachability a partir dos triggers.
  const reachable = new Set<string>();
  const stack = triggers.map((t) => t.id);
  while (stack.length) {
    const id = stack.pop()!;
    if (reachable.has(id)) continue;
    reachable.add(id);
    for (const e of outgoing.get(id) ?? []) stack.push(e.target);
  }

  for (const n of nodes) {
    const inc = incoming.get(n.id) ?? [];
    const out = outgoing.get(n.id) ?? [];
    const t = n.data.meumisterioType;

    if (inc.length === 0 && out.length === 0) {
      issues.push({
        code: 'orphan_node',
        level: 'warning',
        nodeId: n.id,
        message: `"${n.data.label}" não está conectado.`,
      });
      continue;
    }

    if (triggers.length > 0 && t !== 'trigger' && !reachable.has(n.id)) {
      issues.push({
        code: 'unreachable',
        level: 'warning',
        nodeId: n.id,
        message: `"${n.data.label}" não é alcançável a partir do gatilho.`,
      });
    }

    if (out.length === 0 && t !== 'end' && t !== 'anotacao') {
      issues.push({
        code: 'dead_end',
        level: 'warning',
        nodeId: n.id,
        message: `"${n.data.label}" não tem saída — adicione "Fim" ou conecte adiante.`,
      });
    }

    if (t === 'condicao' && out.length < 2) {
      issues.push({
        code: 'condition_no_branches',
        level: 'warning',
        nodeId: n.id,
        message: 'Condição precisa de 2 saídas (verdadeiro / falso).',
      });
    }

    if (!n.data.label.trim()) {
      issues.push({
        code: 'empty_label',
        level: 'warning',
        nodeId: n.id,
        message: 'Sem rótulo.',
      });
    }
  }

  // Ordenação determinística — error antes de warning, depois por ordem natural.
  return issues.sort((a, b) => {
    if (a.level !== b.level) return a.level === 'error' ? -1 : 1;
    return 0;
  });
}

/** Mapa nodeId → nível mais grave entre suas issues (para badge no canvas). */
export function issuesByNode(issues: LintIssue[]): Map<string, LintLevel> {
  const m = new Map<string, LintLevel>();
  for (const i of issues) {
    if (!i.nodeId) continue;
    const curr = m.get(i.nodeId);
    if (curr === 'error') continue; // já está no pior
    if (i.level === 'error' || !curr) m.set(i.nodeId, i.level);
  }
  return m;
}
