import { TextInput } from '../inspector/fields';
import type { Persona } from './vars';

const DEFAULT_KEYS = [
  'lead.nome',
  'lead.cidade',
  'lead.objecao_silenciosa',
  'lead.resumo_dor',
];

interface Props {
  persona: Persona;
  onChange: (next: Persona) => void;
}

export default function PersonaPicker({ persona, onChange }: Props) {
  const keys = Array.from(new Set([...DEFAULT_KEYS, ...Object.keys(persona)]));
  return (
    <div className="space-y-2">
      <div className="text-[11px] uppercase tracking-wide text-slate-400">
        Persona — variáveis do lead
      </div>
      {keys.map((k) => (
        <div key={k} className="grid grid-cols-[140px,1fr] gap-2 items-center">
          <span className="text-[11px] text-slate-400 font-mono truncate" title={k}>
            {k}
          </span>
          <TextInput
            value={persona[k] ?? ''}
            onChange={(v) => onChange({ ...persona, [k]: v })}
            placeholder="—"
          />
        </div>
      ))}
      <p className="text-[10px] text-slate-500 leading-relaxed">
        Use <code className="text-slate-400">{'{{lead.nome}}'}</code> nos textos
        — substituído ao simular.
      </p>
    </div>
  );
}
