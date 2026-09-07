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
    <div className="border-t border-border bg-bg-surface px-3 py-2 text-[11px] text-emerald-500 flex items-center gap-1.5 flex-shrink-0 font-bold">
        <CheckCircle2 className="w-3.5 h-3.5" />
        <span>sem avisos de validação</span>
      </div>
    );
  }

  return (
    <div className="border-t border-border bg-bg-surface flex-shrink-0">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full px-3 py-2 flex items-center justify-between text-[11px] hover:bg-bg-primary transition-colors"
      >
        <span className="flex items-center gap-3">
          {errors > 0 && (
            <span className="flex items-center gap-1 text-red-500 font-bold">
              <AlertCircle className="w-3.5 h-3.5" />
              {errors} erro(s)
            </span>
          )}
          {warnings > 0 && (
            <span className="flex items-center gap-1 text-amber-500 font-bold">
              <AlertTriangle className="w-3.5 h-3.5" />
              {warnings} aviso(s)
            </span>
          )}
        </span>
        <span className="flex items-center gap-1 text-secondary">
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
        <ul className="max-h-44 overflow-y-auto border-t border-border divide-y divide-border/30">
          {issues.map((i, idx) => (
            <li
              key={idx}
              className="px-3 py-2 flex items-center gap-2 text-xs hover:bg-bg-primary transition-colors"
            >
              {i.level === 'error' ? (
                <AlertCircle className="w-3.5 h-3.5 text-red-500 flex-shrink-0" />
              ) : (
                <AlertTriangle className="w-3.5 h-3.5 text-amber-500 flex-shrink-0" />
              )}
              <span className="flex-1 text-primary">{i.message}</span>
              {i.nodeId && (
                <button
                  type="button"
                  onClick={() => onFocus(i.nodeId!)}
                  className="text-[11px] text-accent-amethyst hover:underline flex items-center gap-1 font-bold"
                >
                  <Crosshair className="w-3 h-3" />
                  focar
                </button>
              )}
              <span className="text-[10px] text-secondary font-mono">{i.code}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
