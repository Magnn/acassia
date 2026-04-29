import { Handle, Position, type Node, type NodeProps } from '@xyflow/react';
import { AlertCircle, AlertTriangle } from 'lucide-react';
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

  const isTrigger = d.acassiaType === 'trigger';
  const isEnd = d.acassiaType === 'end';

  return (
    <div
      className={[
        'rounded-2xl border border-border/50 px-0 pb-3 min-w-[220px] max-w-[300px] shadow-premium relative font-sans transition-all duration-300',
        'glass node-gradient',
        d.simActive ? 'ring-2 ring-emerald-500 shadow-glow-emerald animate-pulse' : '',
        !d.simActive && selected ? 'ring-2 ring-accent-amethyst shadow-glow-amethyst' : '',
        !d.simActive && d.lintLevel === 'error' ? 'ring-2 ring-red-500' : '',
      ].join(' ')}
    >
      {/* Top Accent Bar */}
      <div className={['h-1.5 w-full rounded-t-2xl mb-3', v.accent.replace('text-', 'bg-')].join(' ')} />

      {/* Validation Badge */}
      {d.lintLevel && (
        <span
          className={[
            'absolute -top-3 -right-3 rounded-full w-7 h-7 flex items-center justify-center border-2 border-bg-surface shadow-lg z-20',
            d.lintLevel === 'error' ? 'bg-red-500 text-white' : 'bg-amber-400 text-slate-900',
          ].join(' ')}
        >
          {d.lintLevel === 'error' ? (
            <AlertCircle className="w-4 h-4" />
          ) : (
            <AlertTriangle className="w-4 h-4" />
          )}
        </span>
      )}

      {/* Header Container */}
      <div className="px-4 flex items-center justify-between mb-3">
        <div className="flex items-center gap-2.5">
          <div className={['p-1.5 rounded-xl shadow-sm border border-border/50', v.bg].join(' ')}>
            <v.Icon className={['w-4 h-4', v.accent].join(' ')} strokeWidth={2.5} />
          </div>
          <div className="flex flex-col">
            <span className="text-[9px] uppercase tracking-[0.15em] font-black text-secondary/60 leading-none mb-1">
              {v.label}
            </span>
            <span className="text-[14px] font-bold text-primary tracking-tight leading-none">
              {d.label}
            </span>
          </div>
        </div>
      </div>

      {/* Intelligence Section */}
      <div className="px-4 space-y-2">
        {renderPreview(d)}
        {renderConfigHint(d)}
      </div>

      {/* Handles are now styled globally in index.css, just need to position them */}
      {!isTrigger && (
        <Handle
          type="target"
          position={Position.Left}
          className="!bg-accent-amethyst !-left-[6px]"
        />
      )}
      {!isEnd && (
        <Handle
          type="source"
          position={Position.Right}
          className="!bg-accent-amethyst !-right-[6px]"
        />
      )}
    </div>
  );
}

function renderPreview(d: FlowNodeData) {
  const type = d.acassiaType;
  const config = d.config;

  if (type === 'conteudo') {
    const text = config.text || config.message;
    if (typeof text === 'string' && text) {
      return (
        <div className="text-[11px] text-primary/80 leading-relaxed bg-bg-primary/40 p-2.5 rounded-xl border border-border/30 shadow-inner italic">
          "{text.length > 80 ? text.slice(0, 80) + '...' : text}"
        </div>
      );
    }
  }

  if (type === 'condicao') {
    const expr = config.expression || config.logic;
    if (typeof expr === 'string' && expr) {
      return (
        <div className="flex items-center gap-2 text-[10px] font-mono text-indigo-500 bg-indigo-500/5 p-2 rounded-lg border border-indigo-500/20">
          <div className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-pulse" />
          <span>if {expr}</span>
        </div>
      );
    }
  }

  if (type === 'gpt') {
    const prompt = config.prompt || config.system_prompt;
    if (typeof prompt === 'string' && prompt) {
      return (
        <div className="text-[10px] text-emerald-500 bg-emerald-500/5 p-2 rounded-lg border border-emerald-500/20 line-clamp-2">
          <span className="opacity-60 font-bold uppercase mr-1">IA:</span>
          {prompt}
        </div>
      );
    }
  }

  return null;
}

function renderConfigHint(d: FlowNodeData) {
  const seconds = numberField(d.config, 'seconds');
  const keyword = stringField(d.config, 'keyword');
  const moduleHint = stringField(d.config, 'module_hint');

  const hints: { icon: string; text: string }[] = [];
  if (seconds != null) hints.push({ icon: '⌛', text: `${seconds}s` });
  if (keyword) hints.push({ icon: '🔑', text: keyword });
  if (moduleHint) hints.push({ icon: '📦', text: moduleHint });

  if (hints.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-1.5 mt-1">
      {hints.map((h, i) => (
        <span key={i} className="flex items-center gap-1 text-[9px] font-bold px-2 py-0.5 rounded-full bg-secondary/5 text-secondary border border-border/40">
          <span className="text-[10px]">{h.icon}</span>
          {h.text}
        </span>
      ))}
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
