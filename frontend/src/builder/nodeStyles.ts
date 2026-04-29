import {
  Bot,
  Clock,
  GitBranch,
  GitFork,
  MessageSquare,
  Plug,
  Square,
  StickyNote,
  Terminal,
  Zap,
  type LucideIcon,
} from 'lucide-react';

interface NodeVisual {
  Icon: LucideIcon;
  border: string;
  bg: string;
  /** texto do chip "TIPO" no header do node */
  label: string;
  /** cor de acento (Tailwind text-*) — para o ícone */
  accent: string;
}

const VISUALS: Record<string, NodeVisual> = {
  trigger: {
    Icon: Zap,
    border: 'border-violet-400',
    bg: 'bg-violet-950/40',
    accent: 'text-violet-300',
    label: 'Trigger',
  },
  conteudo: {
    Icon: MessageSquare,
    border: 'border-sky-400',
    bg: 'bg-sky-950/40',
    accent: 'text-sky-300',
    label: 'Conteúdo',
  },
  delay: {
    Icon: Clock,
    border: 'border-slate-400',
    bg: 'bg-slate-800/60',
    accent: 'text-slate-300',
    label: 'Delay',
  },
  condicao: {
    Icon: GitBranch,
    border: 'border-amber-400',
    bg: 'bg-amber-950/40',
    accent: 'text-amber-300',
    label: 'Condição',
  },
  gpt: {
    Icon: Bot,
    border: 'border-emerald-400',
    bg: 'bg-emerald-950/40',
    accent: 'text-emerald-300',
    label: 'GPT / IA',
  },
  api: {
    Icon: Plug,
    border: 'border-cyan-400',
    bg: 'bg-cyan-950/40',
    accent: 'text-cyan-300',
    label: 'API',
  },
  ab_split: {
    Icon: GitFork,
    border: 'border-fuchsia-400',
    bg: 'bg-fuchsia-950/40',
    accent: 'text-fuchsia-300',
    label: 'A/B',
  },
  motor_ref: {
    Icon: Terminal,
    border: 'border-rose-400',
    bg: 'bg-rose-950/40',
    accent: 'text-rose-300',
    label: 'Motor Python',
  },
  anotacao: {
    Icon: StickyNote,
    border: 'border-yellow-400',
    bg: 'bg-yellow-950/40',
    accent: 'text-yellow-300',
    label: 'Anotação',
  },
  end: {
    Icon: Square,
    border: 'border-slate-500',
    bg: 'bg-slate-900/60',
    accent: 'text-slate-400',
    label: 'Fim',
  },
};

const FALLBACK: NodeVisual = {
  Icon: Square,
  border: 'border-cigana-border',
  bg: 'bg-cigana-surface',
  accent: 'text-slate-400',
  label: 'Node',
};

export function visualForType(type: string): NodeVisual {
  return VISUALS[type] ?? FALLBACK;
}
