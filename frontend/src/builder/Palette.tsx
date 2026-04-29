import { Layers } from 'lucide-react';
import { visualForType } from './nodeStyles';
import type { AcassiaNodeType } from '../lib/types';

export const DRAG_MIME = 'application/x-acassia-node';

const ITEMS: AcassiaNodeType[] = [
  'trigger',
  'conteudo',
  'delay',
  'condicao',
  'gpt',
  'api',
  'ab_split',
  'motor_ref',
  'anotacao',
  'end',
];

export default function Palette() {
  return (
    <aside className="w-56 flex-shrink-0 border-r border-border bg-bg-sidebar overflow-y-auto">
      <div className="px-3 py-3 flex items-center gap-2 text-[11px] uppercase tracking-wide text-secondary border-b border-border">
        <Layers className="w-3.5 h-3.5" />
        <span>Paleta</span>
      </div>
      <ul className="p-2 space-y-1">
        {ITEMS.map((t) => (
          <PaletteItem key={t} type={t} />
        ))}
      </ul>
      <div className="p-3 text-[11px] text-secondary border-t border-border">
        Arraste para o canvas
      </div>
    </aside>
  );
}

function PaletteItem({ type }: { type: AcassiaNodeType }) {
  const v = visualForType(type);
  return (
    <li
      draggable
      onDragStart={(e) => {
        e.dataTransfer.setData(DRAG_MIME, type);
        e.dataTransfer.effectAllowed = 'copy';
      }}
      className={[
        'rounded border px-2 py-2 cursor-grab active:cursor-grabbing select-none',
        'flex items-center gap-2 text-sm',
        v.border,
        v.bg,
        'hover:brightness-125 transition',
      ].join(' ')}
    >
      <v.Icon className={`w-4 h-4 ${v.accent}`} strokeWidth={2.25} />
      <span className="text-primary">{v.label}</span>
    </li>
  );
}
