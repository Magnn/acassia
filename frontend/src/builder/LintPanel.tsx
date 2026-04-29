import { useState } from 'react';
import type { LintIssue } from './lint';

interface Props {
  issues: LintIssue[];
  onFocus: (nodeId: string) => void;
}

export default function LintPanel({ issues, onFocus }: Props) {
  const [open, setOpen] = useState(false);
  const errors = issues.filter((i) => i.level === 'error').length;
  const warnings = issues.filter((i) => i.level === 'warning').length;

  if (issues.length === 0) {
    return (
      <div className="border-t border-cigana-border bg-cigana-surface px-3 py-1.5 text-[11px] text-emerald-400 flex-shrink-0">
        ✓ sem avisos de validação
      </div>
    );
  }

  return (
    <div className="border-t border-cigana-border bg-cigana-surface flex-shrink-0">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full px-3 py-1.5 flex items-center justify-between text-[11px] hover:bg-cigana-bg/40"
      >
        <span className="flex items-center gap-3">
          {errors > 0 && (
            <span className="text-red-400">● {errors} erro(s)</span>
          )}
          {warnings > 0 && (
            <span className="text-amber-400">⚠ {warnings} aviso(s)</span>
          )}
        </span>
        <span className="text-slate-500">{open ? '▼ ocultar' : '▲ ver lista'}</span>
      </button>
      {open && (
        <ul className="max-h-44 overflow-y-auto border-t border-cigana-border divide-y divide-cigana-border/50">
          {issues.map((i, idx) => (
            <li
              key={idx}
              className="px-3 py-1.5 flex items-baseline gap-2 text-xs hover:bg-cigana-bg/40"
            >
              <span
                className={
                  i.level === 'error' ? 'text-red-400' : 'text-amber-400'
                }
              >
                {i.level === 'error' ? '●' : '⚠'}
              </span>
              <span className="flex-1 text-slate-300">{i.message}</span>
              {i.nodeId && (
                <button
                  type="button"
                  onClick={() => onFocus(i.nodeId!)}
                  className="text-[11px] text-sky-400 hover:underline"
                >
                  focar
                </button>
              )}
              <span className="text-[10px] text-slate-600 font-mono">{i.code}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
