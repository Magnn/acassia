import type { ReactNode } from 'react';
import { Lock } from 'lucide-react';
import { useMyPlan, useMyUsage, useFeature, isPlanAtLeast, type MyUsageEntry } from '../hooks/usePlan';

type Fallback = 'lock' | 'hide' | 'none';

interface FeatureGateProps {
  feature?: string;
  plan?: 'starter' | 'pro' | 'enterprise';
  fallback?: Fallback;
  children: ReactNode;
  /** Customiza CTA do lock overlay; default abre /billing */
  upgradeUrl?: string;
}

/**
 * Esconde/bloqueia conteúdo se user não tem feature ou plano mínimo.
 * Default fallback="lock" — mostra children opaco com lock icon (vendas).
 */
export function FeatureGate({
  feature,
  plan,
  fallback = 'lock',
  children,
  upgradeUrl = '/billing',
}: FeatureGateProps) {
  const { data: myPlan, isLoading } = useMyPlan();
  const { enabled: featureOn } = useFeature(feature || '_unused');

  if (isLoading) {
    // Loading: skeleton sutil (não vaza feature por flash)
    return <div className="animate-pulse opacity-50">{children}</div>;
  }

  let allowed = true;
  if (feature) allowed = featureOn;
  if (allowed && plan && myPlan) {
    allowed = isPlanAtLeast(myPlan.plan, plan);
  }

  if (allowed) return <>{children}</>;

  if (fallback === 'hide' || fallback === 'none') return null;

  return (
    <div className="relative group">
      <div className="opacity-30 pointer-events-none select-none">{children}</div>
      <div className="absolute inset-0 flex items-center justify-center bg-bg-primary/70 backdrop-blur-[2px] rounded-inherit">
        <a
          href={upgradeUrl}
          className="flex items-center gap-2 px-4 py-2 bg-accent-amethyst text-white rounded-xl text-xs font-black uppercase tracking-widest shadow-lg hover:scale-105 transition-all"
        >
          <Lock className="w-3.5 h-3.5" />
          {plan ? `Upgrade pra ${plan}` : 'Upgrade'}
        </a>
      </div>
    </div>
  );
}

interface QuotaGateProps {
  kind: 'leads_month' | 'wa_msgs_month' | 'gemini_tokens_month';
  /** Render-prop com {entry, blocked} — mostra UI customizada baseada no estado. */
  children: (state: {
    entry: MyUsageEntry | null;
    loading: boolean;
    blocked: boolean;
    near_limit: boolean;
  }) => ReactNode;
}

/**
 * Render-prop pra mostrar/customizar UI baseada em quota.
 * Não esconde nada por default — caller decide o que renderizar.
 */
export function QuotaGate({ kind, children }: QuotaGateProps) {
  const { data, isLoading } = useMyUsage();
  const entry = data?.usage?.[kind] ?? null;
  const pct = entry?.pct ?? 0;
  return (
    <>
      {children({
        entry,
        loading: isLoading,
        blocked: !!entry && !entry.unlimited && pct >= 100,
        near_limit: !!entry && !entry.unlimited && pct >= 80,
      })}
    </>
  );
}

/** Barra de progresso de cota com cor dinâmica (verde/amarela/vermelha). */
interface QuotaBarProps {
  kind: 'leads_month' | 'wa_msgs_month' | 'gemini_tokens_month';
  label?: string;
  showCount?: boolean;
}

export function QuotaBar({ kind, label, showCount = true }: QuotaBarProps) {
  const KIND_LABELS: Record<string, string> = {
    leads_month: 'Leads',
    wa_msgs_month: 'Mensagens WhatsApp',
    gemini_tokens_month: 'Tokens IA',
  };
  return (
    <QuotaGate kind={kind}>
      {({ entry, loading }) => {
        if (loading) {
          return <div className="h-2 bg-zinc-800 rounded-full animate-pulse" />;
        }
        if (!entry) return null;
        const displayLabel = label || KIND_LABELS[kind] || kind;
        if (entry.unlimited) {
          return (
            <div>
              <div className="flex justify-between text-[11px] mb-1">
                <span className="text-secondary">{displayLabel}</span>
                <span className="font-mono text-primary">{entry.count.toLocaleString('pt-BR')} / ∞</span>
              </div>
              <div className="h-2 bg-emerald-900/30 rounded-full" />
            </div>
          );
        }
        const pct = entry.pct;
        const color =
          pct >= 100 ? 'bg-red-500' :
          pct >= 95 ? 'bg-red-500' :
          pct >= 80 ? 'bg-amber-500' :
          'bg-emerald-500';
        return (
          <div>
            <div className="flex justify-between text-[11px] mb-1">
              <span className="text-secondary">{displayLabel}</span>
              {showCount && (
                <span className={`font-mono ${pct >= 80 ? 'text-amber-400' : 'text-primary'}`}>
                  {entry.count.toLocaleString('pt-BR')} / {entry.limit.toLocaleString('pt-BR')}
                  <span className="ml-2 text-secondary">({pct}%)</span>
                </span>
              )}
            </div>
            <div className="h-2 bg-bg-surface rounded-full overflow-hidden">
              <div
                className={`h-full ${color} transition-all`}
                style={{ width: `${Math.min(100, pct)}%` }}
              />
            </div>
          </div>
        );
      }}
    </QuotaGate>
  );
}
