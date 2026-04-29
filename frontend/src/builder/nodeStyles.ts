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
  glow?: string;
}

const VISUALS: Record<string, NodeVisual> = {
  trigger: {
    Icon: Zap,
    border: 'border-l-violet-500',
    bg: 'bg-bg-surface/80',
    accent: 'text-violet-500',
    label: 'Trigger',
  },
  conteudo: {
    Icon: MessageSquare,
    border: 'border-l-sky-500',
    bg: 'bg-bg-surface/80',
    accent: 'text-sky-500',
    label: 'Conteúdo',
  },
  delay: {
    Icon: Clock,
    border: 'border-l-amber-500',
    bg: 'bg-bg-surface/80',
    accent: 'text-amber-500',
    label: 'Delay',
  },
  condicao: {
    Icon: GitBranch,
    border: 'border-l-indigo-500',
    bg: 'bg-bg-surface/80',
    accent: 'text-indigo-500',
    label: 'Condição',
  },
  gpt: {
    Icon: Bot,
    border: 'border-l-emerald-500',
    bg: 'bg-bg-surface/80',
    accent: 'text-emerald-500',
    label: 'GPT / IA',
  },
  api: {
    Icon: Plug,
    border: 'border-l-cyan-500',
    bg: 'bg-bg-surface/80',
    accent: 'text-cyan-500',
    label: 'API',
  },
  ab_split: {
    Icon: GitFork,
    border: 'border-l-fuchsia-500',
    bg: 'bg-bg-surface/80',
    accent: 'text-fuchsia-500',
    label: 'A/B',
  },
  motor_ref: {
    Icon: Terminal,
    border: 'border-l-rose-500',
    bg: 'bg-bg-surface/80',
    accent: 'text-rose-500',
    label: 'Motor Python',
  },
  anotacao: {
    Icon: StickyNote,
    border: 'border-l-yellow-400',
    bg: 'bg-yellow-500/5',
    accent: 'text-yellow-600',
    label: 'Anotação',
  },
  end: {
    Icon: Square,
    border: 'border-l-slate-400',
    bg: 'bg-bg-surface/80',
    accent: 'text-slate-500',
    label: 'Fim',
  },
};

const FALLBACK: NodeVisual = {
  Icon: Square,
  border: 'border-l-border',
  bg: 'bg-bg-surface/80',
  accent: 'text-secondary',
  label: 'Node',
};

export function visualForType(type: string): NodeVisual {
  return VISUALS[type] ?? FALLBACK;
}
