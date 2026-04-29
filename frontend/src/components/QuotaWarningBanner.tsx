import { useState } from 'react';
import { Link } from 'react-router-dom';
import { AlertTriangle, X, Zap } from 'lucide-react';
import { useMyUsage } from '../hooks/usePlan';

const KIND_LABELS: Record<string, string> = {
  leads_month: 'leads',
  wa_msgs_month: 'mensagens WhatsApp',
  gemini_tokens_month: 'tokens IA',
};

const STORAGE_KEY = 'acassia_quota_dismiss_v1';

interface DismissState {
  [key: string]: number; // key = `${kind}-${threshold}`, value = timestamp
}

function loadDismissals(): DismissState {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
  } catch {
    return {};
  }
}

function saveDismissal(key: string) {
  const cur = loadDismissals();
  cur[key] = Date.now();
  localStorage.setItem(STORAGE_KEY, JSON.stringify(cur));
}

const DISMISS_VALID_HOURS = 6; // re-mostra após 6h

export default function QuotaWarningBanner() {
  const { data: usage } = useMyUsage();
  const [, forceUpdate] = useState(0);

  if (!usage) return null;

  const dismissals = loadDismissals();
  const now = Date.now();

  // Identifica banners ativos: 100% > 95% > 80%
  const alerts: Array<{ kind: string; pct: number; severity: 'critical' | 'warning' }> = [];
  for (const [kind, entry] of Object.entries(usage.usage)) {
    if (entry.unlimited) continue;
    const pct = entry.pct;
    if (pct >= 100) {
      const dismissKey = `${kind}-100`;
      if (!dismissals[dismissKey] || (now - dismissals[dismissKey]) > DISMISS_VALID_HOURS * 3600 * 1000) {
        alerts.push({ kind, pct, severity: 'critical' });
      }
    } else if (pct >= 80) {
      const dismissKey = `${kind}-80`;
      if (!dismissals[dismissKey] || (now - dismissals[dismissKey]) > DISMISS_VALID_HOURS * 3600 * 1000) {
        alerts.push({ kind, pct, severity: 'warning' });
      }
    }
  }

  if (alerts.length === 0) return null;

  // Mostra o mais crítico só (1 banner por vez)
  alerts.sort((a, b) => b.pct - a.pct);
  const top = alerts[0];

  const isCritical = top.severity === 'critical';
  const dismissKey = `${top.kind}-${isCritical ? 100 : 80}`;

  const dismiss = () => {
    saveDismissal(dismissKey);
    forceUpdate(x => x + 1);
  };

  return (
    <div
      role="alert"
      className={`fixed top-0 left-0 right-0 z-40 px-6 py-2.5 flex items-center justify-between gap-4 border-b ${
        isCritical
          ? 'bg-red-600 border-red-900 text-white'
          : 'bg-amber-500 border-amber-700 text-white'
      }`}
    >
      <div className="flex items-center gap-3 flex-1 min-w-0">
        {isCritical ? (
          <AlertTriangle className="w-4 h-4 animate-pulse flex-shrink-0" />
        ) : (
          <Zap className="w-4 h-4 flex-shrink-0" />
        )}
        <div className="text-xs font-bold truncate">
          {isCritical ? (
            <>
              <strong>Limite atingido:</strong> seus {KIND_LABELS[top.kind] || top.kind} mensais foram esgotados.
              {top.kind === 'leads_month' && ' Novos leads ficarão em fila.'}
              {top.kind === 'wa_msgs_month' && ' Bot não está enviando mensagens.'}
            </>
          ) : (
            <>
              <strong>{Math.round(top.pct)}% usado:</strong> você está próximo do limite de{' '}
              {KIND_LABELS[top.kind] || top.kind}.
            </>
          )}
        </div>
      </div>
      <div className="flex items-center gap-2">
        <Link
          to="/billing"
          className={`px-3 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-widest transition-all ${
            isCritical
              ? 'bg-red-900 hover:bg-red-950 text-white'
              : 'bg-amber-700 hover:bg-amber-800 text-white'
          }`}
        >
          Fazer upgrade
        </Link>
        <button
          onClick={dismiss}
          className="p-1 hover:bg-black/20 rounded"
          aria-label="Fechar aviso"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
