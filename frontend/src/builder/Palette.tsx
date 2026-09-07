import { useState } from 'react';
import { X, Plus, Sparkles, MessageSquare, GitBranch, PlayCircle, Flag } from 'lucide-react';
import { visualForType } from './nodeStyles';
import type { MeuMisterioNodeType } from '../lib/types';

export const DRAG_MIME = 'application/x-meumisterio-node';

interface NodeGroup {
  title: string;
  icon: React.ComponentType<{ className?: string }>;
  items: MeuMisterioNodeType[];
}

const GROUPS: NodeGroup[] = [
  {
    title: 'Canais & Mensagens',
    icon: MessageSquare,
    items: ['trigger', 'conteudo', 'pergunta', 'menu'],
  },
  {
    title: 'Inteligência Artificial',
    icon: Sparkles,
    items: ['agente_ia', 'gpt', 'voice_studio'],
  },
  {
    title: 'Lógica & Roteamento',
    icon: GitBranch,
    items: ['condicao', 'ab_split', 'delay', 'expediente'],
  },
  {
    title: 'Ações & CRM',
    icon: PlayCircle,
    items: ['acao', 'notificar_atendente', 'api', 'integration'],
  },
  {
    title: 'Finalização & Auxiliares',
    icon: Flag,
    items: ['end', 'anotacao'],
  },
];

export default function Palette() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      {/* Floating Action Button (FAB) */}
      <div className="absolute bottom-6 left-6 z-10 flex flex-col items-center gap-2">
        <button
          onClick={() => setIsOpen(!isOpen)}
          className={`w-12 h-12 rounded-2xl flex items-center justify-center text-white shadow-xl transition-all duration-300 hover:scale-105 active:scale-95 ${
            isOpen
              ? 'bg-zinc-800 rotate-45 border border-zinc-700'
              : 'bg-indigo-600 hover:bg-indigo-700 shadow-indigo-500/30'
          }`}
          title={isOpen ? 'Fechar Paleta' : 'Adicionar Nós'}
        >
          <Plus className="w-6 h-6" strokeWidth={2.5} />
        </button>
      </div>

      {/* Modern Slide-over Library Drawer */}
      <aside
        className={`absolute left-0 top-0 w-80 bg-white/95 dark:bg-zinc-950/95 border-r border-zinc-200 dark:border-zinc-800 shadow-2xl backdrop-blur-md flex flex-col h-full z-30 transition-transform duration-300 ease-in-out ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Drawer Header */}
        <div className="px-5 py-4 flex items-center justify-between border-b border-zinc-100 dark:border-zinc-800/80 shrink-0">
          <div>
            <h3 className="font-semibold text-zinc-900 dark:text-zinc-100 text-sm leading-none">
              Biblioteca de Nós
            </h3>
            <p className="text-[11px] text-zinc-400 dark:text-zinc-500 mt-1">
              Arraste os componentes para o canvas
            </p>
          </div>
          <button
            onClick={() => setIsOpen(false)}
            className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 transition-colors p-1.5 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Categorized List */}
        <div className="p-4 flex-1 overflow-y-auto space-y-5 custom-scrollbar">
          {GROUPS.map((group) => {
            const GroupIcon = group.icon;
            return (
              <div key={group.title} className="space-y-2">
                <div className="flex items-center gap-1.5 px-1 text-[11px] font-semibold uppercase tracking-wider text-zinc-400 dark:text-zinc-500">
                  <GroupIcon className="w-3.5 h-3.5" />
                  <span>{group.title}</span>
                </div>
                <div className="flex flex-col gap-1.5">
                  {group.items.map((t) => (
                    <PaletteItem key={t} type={t} />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </aside>
    </>
  );
}

function PaletteItem({ type }: { type: MeuMisterioNodeType }) {
  const v = visualForType(type);
  return (
    <div
      draggable
      onDragStart={(e) => {
        e.dataTransfer.setData(DRAG_MIME, type);
        e.dataTransfer.effectAllowed = 'copy';
      }}
      className="group flex items-center gap-3 px-3 py-2.5 rounded-xl border border-zinc-200/70 dark:border-zinc-800/80 bg-white dark:bg-zinc-900/60 hover:border-indigo-500/60 hover:shadow-md cursor-grab active:cursor-grabbing select-none transition-all duration-150"
    >
      <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 bg-zinc-50 dark:bg-zinc-800/80 border border-zinc-200/50 dark:border-zinc-700/50 group-hover:bg-indigo-50 dark:group-hover:bg-indigo-950/40 transition-colors">
        <v.Icon className={`w-4 h-4 ${v.accent}`} strokeWidth={2} />
      </div>

      <div className="flex flex-col flex-1 min-w-0 justify-center">
        <span className="text-xs font-semibold text-zinc-800 dark:text-zinc-200 leading-tight">
          {v.label}
        </span>
        {v.desc && (
          <span className="text-[10px] text-zinc-400 dark:text-zinc-500 truncate mt-0.5 font-medium leading-tight">
            {v.desc}
          </span>
        )}
      </div>

      {v.badge && (
        <div
          className={`shrink-0 px-1.5 py-0.5 rounded-md text-[9px] font-bold tracking-wide ${v.badge.color}`}
        >
          {v.badge.text}
        </div>
      )}
    </div>
  );
}
