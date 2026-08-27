import {
  Bot,
  CalendarClock,
  Clock,
  GitBranch,
  GitFork,
  HelpCircle,
  List,
  MessageSquare,
  PlayCircle,
  Plug,
  Square,
  StickyNote,
  Terminal,
  UserPlus,
  Network,
  Mic,
  BrainCircuit,
  XCircle,
  Zap,
  type LucideIcon,
} from 'lucide-react';

export interface NodeVisual {
  Icon: LucideIcon;
  border: string;
  bg: string;
  /** texto do chip "TIPO" no header do node */
  label: string;
  /** cor de acento (Tailwind text-*) — para o ícone */
  accent: string;
  glow?: string;
  desc?: string;
  badge?: { text: string; color: string };
}

const VISUALS: Record<string, NodeVisual> = {
  trigger: {
    Icon: Zap,
    border: 'border-l-green-500',
    bg: 'bg-bg-surface/80',
    accent: 'text-green-500',
    label: 'Trigger',
    desc: 'Início do fluxo',
  },
  conteudo: {
    Icon: MessageSquare,
    border: 'border-l-purple-600',
    bg: 'bg-bg-surface/80',
    accent: 'text-purple-600',
    label: 'Conteúdo',
    desc: 'Enviar mensagem de texto, imagem...',
    badge: { text: 'Popular', color: 'bg-slate-100 text-slate-500' },
  },
  pergunta: {
    Icon: HelpCircle,
    border: 'border-l-[#ff5722]',
    bg: 'bg-bg-surface/80',
    accent: 'text-[#ff5722]',
    label: 'Pergunta',
    desc: 'Enviar pergunta',
    badge: { text: 'Popular', color: 'bg-slate-100 text-slate-500' },
  },
  acao: {
    Icon: PlayCircle,
    border: 'border-l-[#2d336b]',
    bg: 'bg-bg-surface/80',
    accent: 'text-[#2d336b]',
    label: 'Ação',
    desc: 'Executar uma ação',
    badge: { text: 'Popular', color: 'bg-slate-100 text-slate-500' },
  },
  delay: {
    Icon: Clock,
    border: 'border-l-amber-500',
    bg: 'bg-bg-surface/80',
    accent: 'text-amber-500',
    label: 'Delay',
    desc: 'Aguardar um período',
  },
  condicao: {
    Icon: GitBranch,
    border: 'border-l-red-500',
    bg: 'bg-bg-surface/80',
    accent: 'text-red-500',
    label: 'Condição',
    desc: 'Validar uma condição',
    badge: { text: 'Popular', color: 'bg-slate-100 text-slate-500' },
  },
  gpt: {
    Icon: Bot,
    border: 'border-l-emerald-500',
    bg: 'bg-bg-surface/80',
    accent: 'text-emerald-500',
    label: 'GPT / Texto',
    desc: 'Gerador de textos GPT',
  },
  agente_ia: {
    Icon: BrainCircuit,
    border: 'border-l-[#8b5cf6]',
    bg: 'bg-bg-surface/80',
    accent: 'text-[#8b5cf6]',
    label: 'Agente IA',
    desc: 'Diálogo inteligente (BETA)',
    badge: { text: 'BETA', color: 'bg-[#8b5cf6] text-white' },
  },
  voice_studio: {
    Icon: Mic,
    border: 'border-l-[#ec4899]',
    bg: 'bg-bg-surface/80',
    accent: 'text-[#ec4899]',
    label: 'Voice Studio',
    desc: 'Gere áudio com modelo',
    badge: { text: 'Popular', color: 'bg-slate-100 text-slate-500' },
  },
  api: {
    Icon: Plug,
    border: 'border-l-cyan-500',
    bg: 'bg-bg-surface/80',
    accent: 'text-cyan-500',
    label: 'API Externa',
    desc: 'Chamada HTTP genérica',
  },
  integration: {
    Icon: Network,
    border: 'border-l-blue-600',
    bg: 'bg-bg-surface/80',
    accent: 'text-blue-600',
    label: 'Integração Nativa',
    desc: 'Apps, Vault e CRMs',
    badge: { text: 'Pro', color: 'bg-[#7c3aed] text-white' },
  },
  ab_split: {
    Icon: GitFork,
    border: 'border-l-fuchsia-500',
    bg: 'bg-bg-surface/80',
    accent: 'text-fuchsia-500',
    label: 'Divisão',
    desc: 'Distribuição de contatos',
  },
  motor_ref: {
    Icon: Terminal,
    border: 'border-l-rose-500',
    bg: 'bg-bg-surface/80',
    accent: 'text-rose-500',
    label: 'Motor Python',
    desc: 'Módulo backend',
  },
  anotacao: {
    Icon: StickyNote,
    border: 'border-l-yellow-400',
    bg: 'bg-yellow-500/5',
    accent: 'text-yellow-600',
    label: 'Anotação',
    desc: 'Apenas organização',
  },
  menu: {
    Icon: List,
    border: 'border-l-slate-600',
    bg: 'bg-bg-surface/80',
    accent: 'text-slate-600',
    label: 'Menu',
    desc: 'Menu de opções',
  },
  expediente: {
    Icon: CalendarClock,
    border: 'border-l-teal-500',
    bg: 'bg-bg-surface/80',
    accent: 'text-teal-500',
    label: 'Expediente',
    desc: 'Adicionar horário de funcionamento',
    badge: { text: 'Novidade', color: 'bg-blue-500 text-white' },
  },
  notificar_atendente: {
    Icon: UserPlus,
    border: 'border-l-indigo-500',
    bg: 'bg-bg-surface/80',
    accent: 'text-indigo-500',
    label: 'Notificar Atendente',
    desc: 'Enviar mensagem para atendente.',
  },
  end: {
    Icon: XCircle,
    border: 'border-l-slate-400',
    bg: 'bg-bg-surface/80',
    accent: 'text-slate-500',
    label: 'Fim',
    desc: 'Encerrar automação',
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
