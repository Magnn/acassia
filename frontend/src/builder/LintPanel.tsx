import { useState } from 'react';
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Crosshair,
} from 'lucide-react';
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
      <div className="border-t border-cigana-border bg-cigana-surface px-3 py-1.5 text-[11px] text-emerald-400 flex items-center gap-1.5 flex-shrink-0">
        <CheckCircle2 className="w-3.5 h-3.5" />
        <span>sem avisos de validação</span>
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
            <span className="flex items-center gap-1 text-red-400">
              <AlertCircle className="w-3.5 h-3.5" />
              {errors} erro(s)
            </span>
          )}
          {warnings > 0 && (
            <span className="flex items-center gap-1 text-amber-400">
              <AlertTriangle className="w-3.5 h-3.5" />
              {warnings} aviso(s)
            </span>
          )}
        </span>
        <span className="flex items-center gap-1 text-slate-500">
          {open ? (
            <>
              <ChevronDown className="w-3 h-3" /> ocultar
            </>
          ) : (
            <>
              <ChevronUp className="w-3 h-3" /> ver lista
            </>
          )}
        </span>
      </button>
      {open && (
        <ul className="max-h-44 overflow-y-auto border-t border-cigana-border divide-y divide-cigana-border/50">
          {issues.map((i, idx) => (
            <li
              key={idx}
              className="px-3 py-1.5 flex items-center gap-2 text-xs hover:bg-cigana-bg/40"
            >
              {i.level === 'error' ? (
                <AlertCircle className="w-3.5 h-3.5 text-red-400 flex-shrink-0" />
              ) : (
                <AlertTriangle className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" />
              )}
              <span className="flex-1 text-slate-300">{i.message}</span>
              {i.nodeId && (
                <button
                  type="button"
                  onClick={() => onFocus(i.nodeId!)}
                  className="text-[11px] text-sky-400 hover:underline flex items-center gap-1"
                >
                  <Crosshair className="w-3 h-3" />
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
