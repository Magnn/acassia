/**
 * components/inbox/ScrollToBottom.tsx — Botão flutuante para ir ao final do chat
 *
 * Aparece quando o usuário rola para cima e tem novas mensagens abaixo.
 * Mostra contador de novas mensagens pendentes.
 */

import { ArrowDown } from 'lucide-react';

interface Props {
  visible: boolean;
  newCount?: number;
  onClick: () => void;
}

export default function ScrollToBottom({ visible, newCount, onClick }: Props) {
  if (!visible) return null;

  return (
    <button
      onClick={onClick}
      className="absolute bottom-28 right-8 z-20 flex items-center gap-2 bg-bg-surface border border-border shadow-premium rounded-full px-4 py-2.5 hover:scale-105 active:scale-95 transition-all animate-scale-in group"
    >
      <ArrowDown className="w-4 h-4 text-accent-amethyst group-hover:translate-y-0.5 transition-transform" />
      {newCount && newCount > 0 ? (
        <span className="text-[10px] font-black text-accent-amethyst tabular-nums">
          {newCount} {newCount === 1 ? 'nova' : 'novas'}
        </span>
      ) : (
        <span className="text-[10px] font-black text-secondary">Ir ao final</span>
      )}
    </button>
  );
}
