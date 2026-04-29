import type { Node } from '@xyflow/react';
import type { FlowNodeData } from '../lib/adapt';

export interface InspectorProps {
  node: Node<FlowNodeData>;
  onUpdate: (patch: Partial<FlowNodeData>) => void;
}

/** Lê campo string do config; vazio se ausente ou não-string. */
export function readStr(cfg: Record<string, unknown>, key: string): string {
  const v = cfg[key];
  return typeof v === 'string' ? v : '';
}

/** Lê campo numérico; '' se ausente ou inválido (compatível com NumberInput). */
export function readNum(cfg: Record<string, unknown>, key: string): number | '' {
  const v = cfg[key];
  if (typeof v === 'number' && Number.isFinite(v)) return v;
  return '';
}

/** Patch utilitário: mantém o resto do config intacto. */
export function patchConfig(
  node: Node<FlowNodeData>,
  patch: Record<string, unknown>,
): Partial<FlowNodeData> {
  return { config: { ...node.data.config, ...patch } };
}
