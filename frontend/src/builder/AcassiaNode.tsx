import { Handle, Position, type Node, type NodeProps } from '@xyflow/react';
import type { FlowNodeData } from '../lib/adapt';
import { visualForType } from './nodeStyles';

export type AcassiaFlowNode = Node<FlowNodeData, 'acassia'>;

/**
 * Custom node único da Fase 1: renderiza qualquer tipo "acassia" com cor + emoji
 * por tipo. Fase 2+ vai dividir em componentes específicos (ContentNode, etc.)
 * com inspetor próprio.
 */
export default function AcassiaNode({ data, selected }: NodeProps<AcassiaFlowNode>) {
  const d = data;
  const v = visualForType(d.acassiaType);

  // Trigger só tem saída; "end" só tem entrada; resto tem ambos.
  const isTrigger = d.acassiaType === 'trigger';
  const isEnd = d.acassiaType === 'end';

  return (
    <div
      className={[
        'rounded-lg border px-3 py-2 min-w-[180px] max-w-[260px] shadow-sm relative',
        v.border,
        v.bg,
        selected ? 'ring-2 ring-cigana-purple' : '',
        d.lintLevel === 'error' ? 'ring-2 ring-red-500' : '',
        d.lintLevel === 'warning' && !selected ? 'ring-1 ring-amber-400' : '',
      ].join(' ')}
    >
      {d.lintLevel && (
        <span
          className={[
            'absolute -top-2 -right-2 rounded-full text-[10px] w-5 h-5 flex items-center justify-center border border-cigana-bg',
            d.lintLevel === 'error' ? 'bg-red-500 text-white' : 'bg-amber-400 text-slate-900',
          ].join(' ')}
          title={d.lintLevel === 'error' ? 'erro de validação' : 'aviso de validação'}
        >
          {d.lintLevel === 'error' ? '!' : '⚠'}
        </span>
      )}
      <div className="flex items-center gap-2 text-[11px] uppercase tracking-wide text-slate-400">
        <span>{v.emoji}</span>
        <span>{v.label}</span>
      </div>
      <div className="mt-1 text-sm font-medium text-slate-100 break-words">
        {d.label}
      </div>
      {renderConfigHint(d)}

      {!isTrigger && (
        <Handle
          type="target"
          position={Position.Left}
          className="!w-2 !h-2 !bg-cigana-purple !border-cigana-bg"
        />
      )}
      {!isEnd && (
        <Handle
          type="source"
          position={Position.Right}
          className="!w-2 !h-2 !bg-cigana-purple !border-cigana-bg"
        />
      )}
    </div>
  );
}

function renderConfigHint(d: FlowNodeData) {
  const stepName = stringField(d.config, 'step_name');
  const seconds = numberField(d.config, 'seconds');
  const keyword = stringField(d.config, 'keyword');
  const moduleHint = stringField(d.config, 'module_hint');

  const hint =
    stepName ||
    (seconds != null ? `${seconds}s` : null) ||
    keyword ||
    moduleHint;

  if (!hint) return null;
  return (
    <div className="mt-1 text-[11px] text-slate-400 break-words line-clamp-2">
      {hint}
    </div>
  );
}

function stringField(o: Record<string, unknown>, k: string): string | null {
  const v = o[k];
  if (typeof v === 'string' && v.trim()) return v;
  return null;
}

function numberField(o: Record<string, unknown>, k: string): number | null {
  const v = o[k];
  if (typeof v === 'number' && Number.isFinite(v)) return v;
  return null;
}
