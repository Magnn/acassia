import { AlertCircle, Check, Circle, Loader2 } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import type { SaveStatus } from './useFlowState';

interface Props {
  status: SaveStatus;
  error: string | null;
}

interface Copy {
  label: string;
  cls: string;
  Icon: LucideIcon;
  spin?: boolean;
}

const COPY: Record<SaveStatus, Copy> = {
  idle: { label: '—', cls: 'text-sibila-smoke', Icon: Circle },
  dirty: { label: 'alterações pendentes', cls: 'text-amber-400', Icon: Circle },
  saving: { label: 'salvando…', cls: 'text-sky-400', Icon: Loader2, spin: true },
  saved: { label: 'salvo', cls: 'text-emerald-400', Icon: Check },
  error: { label: 'erro ao salvar', cls: 'text-red-400', Icon: AlertCircle },
};

export default function SaveIndicator({ status, error }: Props) {
  const { label, cls, Icon, spin } = COPY[status];
  return (
    <span
      className={`text-xs flex items-center gap-1 ${cls}`}
      title={error ?? undefined}
    >
      <Icon
        className={`w-3 h-3 ${spin ? 'animate-spin' : ''}`}
        fill={status === 'dirty' ? 'currentColor' : 'none'}
      />
      <span>{label}</span>
    </span>
  );
}
