/**
 * components/inbox/ConnectionStatus.tsx — Indicador de conexão SSE
 *
 * Dot verde/vermelho discreto no header da inbox.
 */

import { Wifi, WifiOff } from 'lucide-react';

export default function ConnectionStatus({ connected }: { connected: boolean }) {
  return (
    <div
      className={`flex items-center gap-1.5 text-[9px] font-black uppercase tracking-widest transition-all ${
        connected ? 'text-emerald-500' : 'text-rose-400'
      }`}
      title={connected ? 'Conectado em tempo real' : 'Reconectando…'}
    >
      <span
        className={`w-1.5 h-1.5 rounded-full ${
          connected ? 'bg-emerald-500 animate-pulse' : 'bg-rose-400'
        }`}
      />
      {connected ? (
        <Wifi className="w-3 h-3" />
      ) : (
        <WifiOff className="w-3 h-3" />
      )}
    </div>
  );
}
