import { useMyPlan, useMyUsage } from '../hooks/usePlan';
import {
  CreditCard, Zap, Users, MessageSquare, Brain, ArrowRight,
  CheckCircle2, AlertTriangle,
} from 'lucide-react';
import { Link } from 'react-router-dom';

const KIND_META: Record<string, { label: string; icon: typeof Users; description: string }> = {
  leads_month: {
    label: 'Leads',
    icon: Users,
    description: 'Novos contatos capturados este mês',
  },
  wa_msgs_month: {
    label: 'Mensagens WhatsApp',
    icon: MessageSquare,
    description: 'Mensagens enviadas pelo bot este mês',
  },
  gemini_tokens_month: {
    label: 'Tokens IA',
    icon: Brain,
    description: 'Tokens consumidos pelo agente IA Gemini',
  },
};

export default function BillingUsage() {
  const { data: plan, isLoading: planLoading } = useMyPlan();
  const { data: usage, isLoading: usageLoading } = useMyUsage();

  if (planLoading || usageLoading || !plan || !usage) {
    return (
      <div className="p-10 max-w-5xl mx-auto space-y-6 animate-pulse">
        <div className="h-10 w-1/3 bg-bg-surface rounded" />
        <div className="grid grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-40 bg-bg-surface rounded-2xl" />
          ))}
        </div>
      </div>
    );
  }

  const usageEntries = Object.entries(usage.usage);
  const nearLimitCount = usageEntries.filter(
    ([, e]) => !e.unlimited && e.pct >= 80,
  ).length;

  return (
    <div className="p-10 max-w-5xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-black tracking-tight">Uso & Cotas</h1>
          <p className="text-secondary text-sm font-medium mt-1">
            Acompanhe seu consumo este mês
          </p>
        </div>
        <Link
          to="/billing"
          className="flex items-center gap-2 px-5 py-2.5 bg-bg-surface border border-border hover:border-accent-amethyst/30 rounded-xl text-xs font-black uppercase tracking-widest transition-all"
        >
          <CreditCard className="w-3.5 h-3.5" />
          Faturamento
        </Link>
      </div>

      {/* Plan card */}
      <div className="bg-gradient-to-br from-accent-amethyst/10 to-transparent border border-accent-amethyst/20 rounded-3xl p-6">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-[10px] font-black uppercase tracking-widest text-secondary mb-1">
              Seu plano
            </div>
            <div className="flex items-baseline gap-3">
              <h2 className="text-3xl font-black">{plan.label}</h2>
              {plan.price_brl > 0 && (
                <span className="text-secondary font-mono">
                  R${plan.price_brl}/mês
                </span>
              )}
              {plan.source === 'trial' && (
                <span className="px-2 py-0.5 bg-blue-500/10 border border-blue-500/30 rounded text-[10px] font-black uppercase tracking-widest text-blue-400">
                  Trial
                </span>
              )}
              {plan.source === 'override' && (
                <span className="px-2 py-0.5 bg-purple-500/10 border border-purple-500/30 rounded text-[10px] font-black uppercase tracking-widest text-purple-400">
                  Comp
                </span>
              )}
            </div>
          </div>
          {plan.plan !== 'enterprise' && (
            <Link
              to="/billing"
              className="flex items-center gap-2 px-5 py-3 bg-accent-amethyst hover:bg-accent-amethyst/90 text-white rounded-xl text-xs font-black uppercase tracking-widest shadow-lg transition-all"
            >
              Upgrade
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          )}
        </div>
      </div>

      {/* Alert se perto do limite */}
      {nearLimitCount > 0 && (
        <div className="bg-amber-500/10 border border-amber-500/30 rounded-2xl p-4 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm font-black text-amber-400">
              Você está próximo do limite em {nearLimitCount}{' '}
              {nearLimitCount === 1 ? 'cota' : 'cotas'}
            </p>
            <p className="text-xs text-secondary mt-0.5">
              Considere fazer upgrade pra evitar bloqueio quando atingir 100%.
            </p>
          </div>
          <Link
            to="/billing"
            className="px-3 py-1.5 bg-amber-500 hover:bg-amber-400 text-white rounded-lg text-[10px] font-black uppercase tracking-widest"
          >
            Ver planos
          </Link>
        </div>
      )}

      {/* Cards de uso por kind */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {Object.entries(KIND_META).map(([kind, meta]) => {
          const Icon = meta.icon;
          const entry = usage.usage[kind];
          if (!entry) return null;
          return (
            <div
              key={kind}
              className="bg-bg-surface border border-border rounded-3xl p-6"
            >
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-2xl bg-accent-amethyst/10 flex items-center justify-center">
                  <Icon className="w-5 h-5 text-accent-amethyst" />
                </div>
                <div>
                  <h3 className="text-sm font-black tracking-tight">{meta.label}</h3>
                  <p className="text-[10px] text-secondary">{meta.description}</p>
                </div>
              </div>
              <div className="text-3xl font-black tracking-tight mb-1">
                {entry.count.toLocaleString('pt-BR')}
                {!entry.unlimited && (
                  <span className="text-secondary text-base font-bold ml-2">
                    / {entry.limit.toLocaleString('pt-BR')}
                  </span>
                )}
                {entry.unlimited && (
                  <span className="text-emerald-400 text-base font-bold ml-2">/ ∞</span>
                )}
              </div>
              <div className="text-[10px] text-secondary mb-3">
                {entry.unlimited ? 'Sem limite no Enterprise' :
                  entry.remaining !== null && entry.remaining > 0
                    ? `${entry.remaining.toLocaleString('pt-BR')} restantes`
                    : '⚠️ Limite atingido'}
              </div>
              {!entry.unlimited && (
                <div className="h-2 bg-bg-primary rounded-full overflow-hidden">
                  <div
                    className={`h-full transition-all ${
                      entry.pct >= 100 ? 'bg-red-500' :
                      entry.pct >= 95 ? 'bg-red-500' :
                      entry.pct >= 80 ? 'bg-amber-500' :
                      'bg-emerald-500'
                    }`}
                    style={{ width: `${Math.min(100, entry.pct)}%` }}
                  />
                </div>
              )}
              <div className="flex items-center justify-between mt-2 text-[10px]">
                <span className="text-secondary">{entry.pct}% usado</span>
                {entry.cost_brl_cents > 0 && (
                  <span className="text-secondary font-mono">
                    Custo: R${(entry.cost_brl_cents / 100).toFixed(2)}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Features incluídas */}
      <div className="bg-bg-surface border border-border rounded-3xl p-6">
        <h3 className="text-xs font-black uppercase tracking-widest text-secondary mb-4">
          <Zap className="inline w-3.5 h-3.5 mr-2" />
          Features incluídas no seu plano
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {Object.entries(plan.features).map(([feature, enabled]) => {
            const labels: Record<string, string> = {
              branding_removed: 'Branding removido',
              ab_test: 'A/B test em fluxos',
              api_access: 'Acesso à API pública',
              webhooks: 'Webhooks customizados',
              custom_domain: 'Domínio próprio',
              priority_support: 'Suporte prioritário',
              voice_cloning: 'Voice cloning IA',
              marketplace_sell: 'Vender no marketplace',
            };
            return (
              <div
                key={feature}
                className={`flex items-center gap-2 px-3 py-2 rounded-xl ${
                  enabled
                    ? 'bg-emerald-500/5 border border-emerald-500/20'
                    : 'bg-zinc-900/30 border border-zinc-800 opacity-50'
                }`}
              >
                {enabled ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                ) : (
                  <div className="w-4 h-4 rounded-full border border-zinc-700 flex-shrink-0" />
                )}
                <span className={`text-xs font-bold ${enabled ? 'text-primary' : 'text-secondary line-through'}`}>
                  {labels[feature] || feature}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Reset info */}
      <div className="text-center text-[11px] text-secondary">
        Cotas renovam automaticamente no dia 1º do próximo mês.
      </div>
    </div>
  );
}
