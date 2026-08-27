import { useState } from 'react';
import { X, Plus } from 'lucide-react';
import { visualForType, type NodeVisual } from './nodeStyles';
import type { MeuMisterioNodeType } from '../lib/types';

export const DRAG_MIME = 'application/x-meumisterio-node';

const ITEMS: MeuMisterioNodeType[] = [
  'trigger',
  'menu',
  'conteudo',
  'pergunta',
  'acao',
  'delay',
  'expediente',
  'condicao',
  'notificar_atendente',
  'ab_split',
  'api',
  'integration',
  'gpt',
  'agente_ia',
  'voice_studio',
  'anotacao',
  'end',
];

export default function Palette() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      {/* Botão Flutuante (FAB) - z-10 para ficar atrás da Paleta */}
      <div className="absolute bottom-6 left-6 z-10 flex flex-col items-center gap-2">
         <button
            onClick={() => setIsOpen(!isOpen)}
            className={`w-[52px] h-[52px] rounded-full flex items-center justify-center text-white shadow-lg transition-transform duration-300 hover:scale-105 active:scale-95 ${isOpen ? 'bg-[#7e22ce] rotate-45' : 'bg-[#9333ea] rotate-0'}`}
         >
            <Plus className="w-8 h-8" strokeWidth={2.5} />
         </button>
      </div>

      {/* Painel Retrátil da Paleta - z-20 para cobrir o FAB */}
      <aside 
        className={`absolute left-0 top-0 w-[280px] bg-white border-r border-slate-200 shadow-[4px_0_24px_rgba(0,0,0,0.06)] flex flex-col h-full z-20 transition-transform duration-300 ease-in-out ${isOpen ? 'translate-x-0' : '-translate-x-full'}`}
      >
        <div className="px-4 py-4 flex items-center justify-between border-b border-slate-100 shrink-0">
          <span className="font-bold text-slate-800 text-[15px]">Menu de opções</span>
          <button 
             onClick={() => setIsOpen(false)}
             className="text-slate-400 hover:text-slate-600 transition-colors bg-slate-100 p-1.5 rounded-full"
          >
             <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-3 flex-1 overflow-y-auto custom-scrollbar">
           <div className="flex flex-col gap-2">
             {ITEMS.map((t) => (
               <PaletteItem key={t} type={t} />
             ))}
           </div>
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
      className="group flex items-center gap-3 px-3 py-2.5 rounded-lg border border-slate-100 bg-white hover:border-violet-400 hover:shadow-md cursor-grab active:cursor-grabbing select-none transition-all duration-200"
    >
      <div className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0 bg-slate-50 border border-slate-100 group-hover:bg-violet-50 transition-colors">
         <v.Icon className={`w-[18px] h-[18px] ${v.accent}`} strokeWidth={2} />
      </div>
      
      <div className="flex flex-col flex-1 min-w-0 justify-center">
         <span className="text-[13px] font-semibold text-slate-800 leading-tight">
            {v.label}
         </span>
         {v.desc && (
            <span className="text-[10.5px] text-slate-400 truncate mt-0.5 font-medium leading-tight">
               {v.desc}
            </span>
         )}
      </div>

      {v.badge && (
         <div className={`shrink-0 px-2 py-0.5 rounded-full text-[9px] font-bold tracking-wide ${v.badge.color}`}>
            {v.badge.text}
         </div>
      )}
    </div>
  );
}
