import { type ReactNode } from 'react';

const baseInput =
  'w-full rounded-[10px] border border-[#e2e8f0] bg-[#f1f5f9] px-[9px] py-[7px] text-[13px] text-slate-800 ' +
  'placeholder:text-slate-400 focus:outline-none focus:border-[#6366f1] focus:ring-[3px] focus:ring-[rgba(99,102,241,0.14)] focus:bg-white transition-colors ' +
  'font-[Inter,ui-sans-serif,system-ui,sans-serif]';

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
        <span className="text-[12px] font-semibold text-[#475569] tracking-tight block mb-1.5" style={{ letterSpacing: '-0.01em' }}>
          {label}
        </span>
        {hint && <span className="text-[10px] text-slate-400">{hint}</span>}
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
