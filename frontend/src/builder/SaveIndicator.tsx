import type { SaveStatus } from './useFlowState';

interface Props {
  status: SaveStatus;
  error: string | null;
}

const COPY: Record<SaveStatus, { label: string; cls: string }> = {
  idle: { label: '—', cls: 'text-slate-500' },
  dirty: { label: '● alterações pendentes', cls: 'text-amber-400' },
  saving: { label: '↻ salvando…', cls: 'text-sky-400' },
  saved: { label: '✓ salvo', cls: 'text-emerald-400' },
  error: { label: '⚠ erro ao salvar', cls: 'text-red-400' },
};

export default function SaveIndicator({ status, error }: Props) {
  const { label, cls } = COPY[status];
  return (
    <span className={`text-xs ${cls}`} title={error ?? undefined}>
      {label}
    </span>
  );
}
