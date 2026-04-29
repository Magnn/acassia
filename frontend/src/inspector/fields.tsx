import { type ReactNode } from 'react';

const baseInput =
  'w-full rounded border border-cigana-border bg-cigana-bg px-2 py-1.5 text-sm text-slate-100 ' +
  'placeholder:text-slate-500 focus:outline-none focus:border-cigana-purple';

export function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <label className="block">
      <div className="mb-1 flex items-baseline justify-between">
        <span className="text-[11px] uppercase tracking-wide text-slate-400">
          {label}
        </span>
        {hint && <span className="text-[10px] text-slate-500">{hint}</span>}
      </div>
      {children}
    </label>
  );
}

export function TextInput({
  value,
  onChange,
  placeholder,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}) {
  return (
    <input
      type="text"
      className={baseInput}
      value={value}
      placeholder={placeholder}
      onChange={(e) => onChange(e.target.value)}
    />
  );
}

export function NumberInput({
  value,
  onChange,
  min,
  max,
  placeholder,
}: {
  value: number | '';
  onChange: (v: number | '') => void;
  min?: number;
  max?: number;
  placeholder?: string;
}) {
  return (
    <input
      type="number"
      className={baseInput}
      value={value}
      min={min}
      max={max}
      placeholder={placeholder}
      onChange={(e) => {
        const raw = e.target.value;
        if (raw === '') return onChange('');
        const n = Number(raw);
        onChange(Number.isFinite(n) ? n : '');
      }}
    />
  );
}

export function TextArea({
  value,
  onChange,
  rows = 4,
  placeholder,
}: {
  value: string;
  onChange: (v: string) => void;
  rows?: number;
  placeholder?: string;
}) {
  return (
    <textarea
      className={`${baseInput} resize-y leading-relaxed`}
      rows={rows}
      value={value}
      placeholder={placeholder}
      onChange={(e) => onChange(e.target.value)}
    />
  );
}

export function Select<T extends string>({
  value,
  onChange,
  options,
}: {
  value: T;
  onChange: (v: T) => void;
  options: { value: T; label: string }[];
}) {
  return (
    <select
      className={baseInput}
      value={value}
      onChange={(e) => onChange(e.target.value as T)}
    >
      {options.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </select>
  );
}
