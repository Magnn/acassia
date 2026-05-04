import type { Edge, Node } from '@xyflow/react';
import type { FlowNodeData } from '../lib/adapt';
import type { Card } from '../inspector/conteudo/types';
import { substitute, type Persona } from './vars';

export type SimStep =
  | { kind: 'enter'; nodeId: string; label: string; type: string }
  | { kind: 'text'; nodeId: string; text: string }
  | { kind: 'media'; nodeId: string; mediaType: 'image' | 'audio' | 'video' | 'document'; url: string; caption: string }
  | { kind: 'delay'; nodeId: string; seconds: number }
  | { kind: 'choice'; nodeId: string; question: string }
  | { kind: 'stub'; nodeId: string; label: string; detail: string }
  | { kind: 'end'; nodeId: string; label: string }
  | { kind: 'halt'; reason: string };

export interface WalkerControl {
  /** Resolve com true para a saída "verdadeira" / false para "falsa" do Condição. */
  awaitChoice: () => Promise<boolean>;
}

interface WalkContext {
  nodes: Node<FlowNodeData>[];
  edges: Edge[];
  persona: Persona;
  control: WalkerControl;
}

export async function* walk(ctx: WalkContext): AsyncGenerator<SimStep> {
  const byId = new Map(ctx.nodes.map((n) => [n.id, n]));
  const trigger = ctx.nodes.find((n) => n.data.meumisterioType === 'trigger');
  if (!trigger) {
    yield { kind: 'halt', reason: 'sem nó "trigger"' };
    return;
  }

  let current: string | null = trigger.id;
  const visited = new Set<string>();

  while (current) {
    if (visited.has(current)) {
      yield { kind: 'halt', reason: `loop detectado em ${current}` };
      return;
    }
    visited.add(current);

    const node = byId.get(current);
    if (!node) {
      yield { kind: 'halt', reason: `nó ${current} não existe` };
      return;
    }

    yield {
      kind: 'enter',
      nodeId: node.id,
      label: node.data.label,
      type: node.data.meumisterioType,
    };

    const t = node.data.meumisterioType;

    if (t === 'end') {
      yield { kind: 'end', nodeId: node.id, label: node.data.label };
      return;
    }

    let nextId: string | null;
    if (t === 'condicao') {
      yield { kind: 'choice', nodeId: node.id, question: 'A condição passou?' };
      const ok = await ctx.control.awaitChoice();
      nextId = pickCondicaoBranch(node, ok, ctx);
    } else {
      yield* emitForNode(node, ctx);
      nextId = pickFirstOutgoing(node.id, ctx.edges);
    }

    current = nextId;
  }

  yield { kind: 'halt', reason: 'fim de caminho (sem próxima aresta)' };
}

function pickFirstOutgoing(nodeId: string, edges: Edge[]): string | null {
  const e = edges.find((x) => x.source === nodeId);
  return e ? e.target : null;
}

function pickCondicaoBranch(
  node: Node<FlowNodeData>,
  ok: boolean,
  ctx: WalkContext,
): string | null {
  const cfg = node.data.config;
  const out = ctx.edges.filter((e) => e.source === node.id);
  const trueTarget = String(cfg.true_to ?? '') || null;
  const falseTarget = String(cfg.false_to ?? '') || null;
  const exists = (id: string) => ctx.nodes.some((n) => n.id === id);
  if (ok) return trueTarget && exists(trueTarget) ? trueTarget : out[0]?.target ?? null;
  return falseTarget && exists(falseTarget) ? falseTarget : out[1]?.target ?? out[0]?.target ?? null;
}

async function* emitForNode(
  node: Node<FlowNodeData>,
  ctx: WalkContext,
): AsyncGenerator<SimStep> {
  const t = node.data.meumisterioType;
  const cfg = node.data.config;

  if (t === 'trigger' || t === 'anotacao') return;

  if (t === 'delay') {
    const s = Number(cfg.seconds);
    yield { kind: 'delay', nodeId: node.id, seconds: Number.isFinite(s) ? s : 0 };
    return;
  }

  if (t === 'conteudo') {
    yield* emitConteudo(node, ctx);
    return;
  }

  if (t === 'gpt') {
    const sys = String(cfg.system_prompt ?? '');
    yield {
      kind: 'stub',
      nodeId: node.id,
      label: 'IA / GPT',
      detail: sys ? `system: ${sys.slice(0, 80)}…` : '(sem system prompt)',
    };
    return;
  }

  if (t === 'api') {
    yield {
      kind: 'stub',
      nodeId: node.id,
      label: 'API',
      detail: `${cfg.method ?? 'GET'} ${cfg.url ?? '(sem URL)'}`,
    };
    return;
  }

  if (t === 'ab_split') {
    const a = Number(cfg.weight_a ?? 50);
    const b = Number(cfg.weight_b ?? 50);
    yield {
      kind: 'stub',
      nodeId: node.id,
      label: 'A/B Split',
      detail: `pesos ${a} / ${b} — escolha aleatória neste node`,
    };
    return;
  }

  if (t === 'motor_ref') {
    yield {
      kind: 'stub',
      nodeId: node.id,
      label: 'Motor Python',
      detail: String(cfg.module_hint ?? '(módulo não especificado)'),
    };
    return;
  }

  yield { kind: 'stub', nodeId: node.id, label: t, detail: '(tipo desconhecido)' };
}

async function* emitConteudo(
  node: Node<FlowNodeData>,
  ctx: WalkContext,
): AsyncGenerator<SimStep> {
  const raw = node.data.config.contents;
  const cards: Card[] = Array.isArray(raw) ? raw.filter(isCard) : [];
  if (cards.length === 0) {
    const txt = String(node.data.config.text ?? node.data.config.body ?? '');
    if (txt) yield { kind: 'text', nodeId: node.id, text: substitute(txt, ctx.persona) };
    return;
  }
  for (const c of cards) {
    if (c.type === 'text') {
      yield { kind: 'text', nodeId: node.id, text: substitute(c.value, ctx.persona) };
    } else if (c.type === 'delay') {
      yield { kind: 'delay', nodeId: node.id, seconds: c.value };
    } else {
      yield {
        kind: 'media',
        nodeId: node.id,
        mediaType: c.type,
        url: substitute(c.value.url, ctx.persona),
        caption: substitute(c.value.caption, ctx.persona),
      };
    }
  }
}

function isCard(x: unknown): x is Card {
  if (!x || typeof x !== 'object') return false;
  const t = (x as { type?: unknown }).type;
  return t === 'text' || t === 'delay' || t === 'image' || t === 'audio' || t === 'video' || t === 'document';
}
