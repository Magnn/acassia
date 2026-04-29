// Mapa visual por tipo de node — Tailwind classes + emoji.
// Espelha aproximadamente os ícones FontAwesome do dashboard.html.

interface NodeVisual {
  emoji: string;
  border: string; // tailwind border color
  bg: string; // tailwind background tint
  label: string; // texto curto pro chip de tipo
}

const VISUALS: Record<string, NodeVisual> = {
  trigger: { emoji: '⚡', border: 'border-violet-400', bg: 'bg-violet-950/40', label: 'Trigger' },
  conteudo: { emoji: '💬', border: 'border-sky-400', bg: 'bg-sky-950/40', label: 'Conteúdo' },
  delay: { emoji: '⏱️', border: 'border-slate-400', bg: 'bg-slate-800/60', label: 'Delay' },
  condicao: { emoji: '🔀', border: 'border-amber-400', bg: 'bg-amber-950/40', label: 'Condição' },
  gpt: { emoji: '🧠', border: 'border-emerald-400', bg: 'bg-emerald-950/40', label: 'GPT / IA' },
  api: { emoji: '🔌', border: 'border-cyan-400', bg: 'bg-cyan-950/40', label: 'API' },
  ab_split: { emoji: '🎲', border: 'border-fuchsia-400', bg: 'bg-fuchsia-950/40', label: 'A/B' },
  motor_ref: { emoji: '🐍', border: 'border-rose-400', bg: 'bg-rose-950/40', label: 'Motor Python' },
  anotacao: { emoji: '📝', border: 'border-yellow-400', bg: 'bg-yellow-950/40', label: 'Anotação' },
  end: { emoji: '⏹️', border: 'border-slate-500', bg: 'bg-slate-900/60', label: 'Fim' },
};

const FALLBACK: NodeVisual = {
  emoji: '⬚',
  border: 'border-cigana-border',
  bg: 'bg-cigana-surface',
  label: 'Node',
};

export function visualForType(type: string): NodeVisual {
  return VISUALS[type] ?? FALLBACK;
}
