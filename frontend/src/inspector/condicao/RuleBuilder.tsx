import { Select, TextInput } from '../fields';

export interface Rule {
  var: string;
  op: string;
  value: string;
}

export type Logic = 'AND' | 'OR';

interface Props {
  rules: Rule[];
  logic: Logic;
  onRulesChange: (next: Rule[]) => void;
  onLogicChange: (next: Logic) => void;
}

const OPS = [
  { value: 'equals', label: 'igual a' },
  { value: 'not_equals', label: 'diferente de' },
  { value: 'contains', label: 'contém' },
  { value: 'not_contains', label: 'não contém' },
  { value: 'starts_with', label: 'começa com' },
  { value: 'ends_with', label: 'termina com' },
  { value: 'gt', label: 'maior que' },
  { value: 'lt', label: 'menor que' },
  { value: 'empty', label: 'está vazio' },
  { value: 'not_empty', label: 'não está vazio' },
];

const NO_VALUE_OPS = new Set(['empty', 'not_empty']);

export default function RuleBuilder({
  rules,
  logic,
  onRulesChange,
  onLogicChange,
}: Props) {
  const update = (i: number, patch: Partial<Rule>) => {
    const next = rules.slice();
    next[i] = { ...next[i], ...patch };
    onRulesChange(next);
  };
  const remove = (i: number) => {
    const next = rules.slice();
    next.splice(i, 1);
    onRulesChange(next);
  };
  const add = () => onRulesChange([...rules, { var: '', op: 'equals', value: '' }]);

  return (
    <div className="space-y-3">
      {rules.length > 1 && (
        <div className="flex items-center gap-2">
          <span className="text-[11px] uppercase tracking-wide text-slate-400">
            Combinar regras
          </span>
          <div className="inline-flex rounded border border-cigana-border overflow-hidden text-xs">
            {(['AND', 'OR'] as const).map((l) => (
              <button
                key={l}
                type="button"
                onClick={() => onLogicChange(l)}
                className={[
                  'px-3 py-1',
                  logic === l
                    ? 'bg-cigana-purple text-white'
                    : 'bg-cigana-bg text-slate-300 hover:bg-cigana-surface',
                ].join(' ')}
              >
                {l === 'AND' ? 'Todas (E)' : 'Qualquer (OU)'}
              </button>
            ))}
          </div>
        </div>
      )}

      <ol className="space-y-2">
        {rules.map((r, i) => (
          <li
            key={i}
            className="rounded border border-cigana-border bg-cigana-bg p-2 space-y-2"
          >
            <div className="flex items-center justify-between text-[11px] uppercase tracking-wide text-slate-400">
              <span>Regra {i + 1}</span>
              <button
                type="button"
                onClick={() => remove(i)}
                className="px-1 hover:text-red-400"
                title="Remover regra"
              >
                ×
              </button>
            </div>
            <TextInput
              value={r.var}
              onChange={(v) => update(i, { var: v })}
              placeholder="lead.nome / ctx.metadata.x"
            />
            <Select
              value={r.op}
              onChange={(v) => update(i, { op: v })}
              options={OPS}
            />
            {!NO_VALUE_OPS.has(r.op) && (
              <TextInput
                value={r.value}
                onChange={(v) => update(i, { value: v })}
                placeholder="Compare contra…"
              />
            )}
          </li>
        ))}
      </ol>

      <button
        type="button"
        onClick={add}
        className="w-full text-xs px-2 py-1 rounded border border-dashed border-cigana-border text-slate-400 hover:text-slate-100 hover:border-cigana-purple"
      >
        + adicionar regra
      </button>
    </div>
  );
}
