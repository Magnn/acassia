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
    border: 'border-l-violet-500',
    bg: 'bg-white',
    accent: 'text-violet-600',
    label: 'Trigger',
  },
  conteudo: {
    Icon: MessageSquare,
    border: 'border-l-sky-500',
    bg: 'bg-white',
    accent: 'text-sky-600',
    label: 'Conteúdo',
  },
  delay: {
    Icon: Clock,
    border: 'border-l-slate-400',
    bg: 'bg-white',
    accent: 'text-slate-500',
    label: 'Delay',
  },
  condicao: {
    Icon: GitBranch,
    border: 'border-l-amber-500',
    bg: 'bg-white',
    accent: 'text-amber-600',
    label: 'Condição',
  },
  gpt: {
    Icon: Bot,
    border: 'border-l-emerald-500',
    bg: 'bg-white',
    accent: 'text-emerald-600',
    label: 'GPT / IA',
  },
  api: {
    Icon: Plug,
    border: 'border-l-cyan-500',
    bg: 'bg-white',
    accent: 'text-cyan-600',
    label: 'API',
  },
  ab_split: {
    Icon: GitFork,
    border: 'border-l-fuchsia-500',
    bg: 'bg-white',
    accent: 'text-fuchsia-600',
    label: 'A/B',
  },
  motor_ref: {
    Icon: Terminal,
    border: 'border-l-rose-500',
    bg: 'bg-white',
    accent: 'text-rose-600',
    label: 'Motor Python',
  },
  anotacao: {
    Icon: StickyNote,
    border: 'border-l-yellow-400',
    bg: 'bg-[#fffdf0]', // Slightly yellow tinted bg for annotations
    accent: 'text-yellow-600',
    label: 'Anotação',
  },
  end: {
    Icon: Square,
    border: 'border-l-slate-400',
    bg: 'bg-white',
    accent: 'text-slate-500',
    label: 'Fim',
  },
};

const FALLBACK: NodeVisual = {
  Icon: Square,
  border: 'border-l-slate-300',
  bg: 'bg-white',
  accent: 'text-slate-500',
  label: 'Node',
};

export function visualForType(type: string): NodeVisual {
  return VISUALS[type] ?? FALLBACK;
}
