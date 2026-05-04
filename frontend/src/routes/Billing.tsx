import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  ArrowRight, Check, X as XIcon,
  ExternalLink, ShieldCheck, AlertTriangle, Crown,
  Calendar, Zap, AlertCircle,
} from 'lucide-react';
import { billingApi } from '../api/billing';
import { useMyPlan } from '../hooks/usePlan';
import { toast } from '../lib/toast';
import { ApiError } from '../api/client';

interface PlanCard {
  id: string;
  name: string;
  price_monthly: number;
  price_annual: number;
  description: string;
  features: Array<{ label: string; included: boolean }>;
  popular?: boolean;
  highlight?: 'best_value' | 'most_popular';
}

const PLANS: PlanCard[] = [
  {
    id: 'starter',
    name: 'Starter',
    price_monthly: 97,
    price_annual: 932,  // 80/mês equivalente
    description: 'Pra começar a automatizar consultas',
    features: [
      { label: 'Até 500 leads/mês', included: true },
      { label: '5.000 mensagens WhatsApp/mês', included: true },
      { label: '1 fluxo + 1 atendente IA', included: true },
      { label: '100k tokens IA Gemini/mês', included: true },
      { label: 'Voice cloning', included: false },
      { label: 'A/B test em fluxos', included: false },
      { label: 'Branding removido', included: false },
      { label: 'Suporte prioritário', included: false },
    ],
  },
  {
    id: 'pro',
    name: 'Pro',
    price_monthly: 197,
    price_annual: 1894,
    description: 'Cresça e escale com IA',
    popular: true,
    highlight: 'most_popular',
    features: [
      { label: 'Até 5.000 leads/mês', included: true },
      { label: '50.000 mensagens WhatsApp/mês', included: true },
      { label: '5 fluxos + 3 atendentes', included: true },
      { label: '1M tokens IA/mês', included: true },
      { label: 'Voice cloning IA (ElevenLabs)', included: true },
      { label: 'A/B test em fluxos', included: true },
      { label: 'Branding removido', included: true },
      { label: 'Suporte prioritário', included: true },
    ],
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    price_monthly: 497,
    price_annual: 4771,
    description: 'Pra operações grandes',
    features: [
      { label: 'Leads ilimitados', included: true },
      { label: 'Mensagens ilimitadas', included: true },
      { label: 'Fluxos + atendentes ilimitados', included: true },
      { label: '10M tokens IA/mês', included: true },
      { label: 'Voice cloning + Studio premium', included: true },
      { label: 'API pública + webhooks', included: true },
      { label: 'Domínio próprio', included: true },
      { label: 'Suporte dedicado + SLA', included: true },
    ],
  },
];

const PLAN_RANK: Record<string, number> = { free: 0, starter: 1, pro: 2, enterprise: 3 };

export default function Billing() {
  const qc = useQueryClient();
  const [billingPeriod, setBillingPeriod] = useState<'monthly' | 'annual'>('monthly');
  const [actionPending, setActionPending] = useState<string | null>(null);

  const { data: state, isLoading: stateLoading } = useQuery({
    queryKey: ['billing-state'],
    queryFn: billingApi.getState,
  });
  const { data: myPlan } = useMyPlan();

  const checkoutMutation = useMutation({
    mutationFn: (plan: string) => billingApi.startCheckout(plan, { billing_period: billingPeriod }),
    onSuccess: (res) => {
      if (res?.url) window.location.href = res.url;
      else toast.error(res?.error || 'Falha ao abrir checkout');
    },
    onError: (e: Error) => toast.error(`Erro: ${e.message}`),
    onSettled: () => setActionPending(null),
  });

  const portalMutation = useMutation({
    mutationFn: billingApi.openPortal,
    onSuccess: (res) => {
      if (res?.url) window.location.href = res.url;
      else toast.error(res?.error || 'Falha ao abrir portal');
    },
  });

  const upgradeMutation = useMutation({
    mutationFn: ({ plan }: { plan: string }) => billingApi.upgrade(plan, billingPeriod),
    onSuccess: (res) => {
      toast.success(res.message);
      qc.invalidateQueries({ queryKey: ['billing-state'] });
      qc.invalidateQueries({ queryKey: ['me', 'plan'] });
    },
    onError: handleBillingError,
    onSettled: () => setActionPending(null),
  });

  const downgradeMutation = useMutation({
    mutationFn: ({ plan }: { plan: string }) => billingApi.downgrade(plan, billingPeriod),
    onSuccess: (res) => {
      toast.success(res.message);
      qc.invalidateQueries({ queryKey: ['billing-state'] });
    },
    onError: handleBillingError,
    onSettled: () => setActionPending(null),
  });

  const cancelPendingMutation = useMutation({
    mutationFn: billingApi.cancelPendingDowngrade,
    onSuccess: () => {
      toast.success('Downgrade cancelado');
      qc.invalidateQueries({ queryKey: ['billing-state'] });
    },
  });

  const abortCancellationMut = useMutation({
    mutationFn: billingApi.abortCancellation,
    onSuccess: (res) => {
      toast.success(res.message);
      qc.invalidateQueries({ queryKey: ['billing-state'] });
    },
  });

  const currentPlan = state?.effective_plan || 'free';
  const currentRank = PLAN_RANK[currentPlan] ?? 0;
  const hasActiveSubscription = state?.billing?.has_subscription ?? false;
  const billing = state?.billing;

  const annualSavings = useMemo(() => {
    return PLANS.map(p => Math.round((p.price_monthly * 12 - p.price_annual) / (p.price_monthly * 12) * 100));
  }, []);

  if (stateLoading) {
    return (
      <div className="p-10 max-w-7xl mx-auto animate-pulse space-y-8">
        <div className="h-12 w-1/3 bg-bg-surface rounded mx-auto" />
        <div className="grid grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-96 bg-bg-surface rounded-3xl" />
          ))}
        </div>
      </div>
    );
  }

  function handleAction(planId: string, action: 'start' | 'upgrade' | 'downgrade') {
    setActionPending(planId);
    if (action === 'start') checkoutMutation.mutate(planId);
    else if (action === 'upgrade') upgradeMutation.mutate({ plan: planId });
    else downgradeMutation.mutate({ plan: planId });
  }

  return (
    <div className="p-10 max-w-7xl mx-auto space-y-12">
      {/* Header */}
      <div className="text-center space-y-4">
        <h1 className="text-4xl font-black tracking-tight">
          Sua Assinatura <span className="text-accent-amethyst">Meu Mistério</span>
        </h1>
        <p className="text-secondary font-medium max-w-2xl mx-auto">
          Escolha o plano ideal pra escalar seu atendimento espiritual
        </p>
      </div>

      {/* Status atual */}
      {billing && billing.has_subscription && (
        <CurrentSubscriptionCard
          billing={billing}
          effective_plan={state.effective_plan}
          onCancelPending={() => cancelPendingMutation.mutate()}
          onAbortCancellation={() => abortCancellationMut.mutate()}
          onPortal={() => portalMutation.mutate()}
        />
      )}

      {/* Trial banner se em trial */}
      {state?.effective_source === 'trial' && (
        <div className="bg-blue-500/10 border border-blue-500/30 rounded-3xl p-6 flex items-center gap-4 max-w-3xl mx-auto">
          <div className="w-12 h-12 rounded-2xl bg-blue-500/20 flex items-center justify-center flex-shrink-0">
            <Zap className="w-6 h-6 text-blue-400" />
          </div>
          <div className="flex-1">
            <div className="text-xs font-black uppercase tracking-widest text-blue-400">Trial Pro Ativo</div>
            <div className="text-sm font-bold mt-0.5">
              Você tem todos os recursos Pro grátis por 14 dias.
              {myPlan && <span className="text-secondary ml-2">Adicione cartão pra continuar após o trial.</span>}
            </div>
          </div>
        </div>
      )}

      {/* Override / Comp banner */}
      {state?.effective_source === 'override' && (
        <div className="bg-purple-500/10 border border-purple-500/30 rounded-3xl p-6 flex items-center gap-4 max-w-3xl mx-auto">
          <Crown className="w-6 h-6 text-purple-400 flex-shrink-0" />
          <div className="text-sm">
            Plano <strong className="text-purple-300">{state.effective_label}</strong> ativo via cortesia da equipe Meu Mistério.
          </div>
        </div>
      )}

      {/* Toggle Mensal/Anual */}
      <div className="flex justify-center">
        <div className="bg-bg-surface border border-border rounded-2xl p-1 flex gap-1">
          {(['monthly', 'annual'] as const).map((period) => (
            <button
              key={period}
              onClick={() => setBillingPeriod(period)}
              className={`px-6 py-2 rounded-xl text-xs font-black uppercase tracking-widest transition-all ${
                billingPeriod === period
                  ? 'bg-accent-amethyst text-white'
                  : 'text-secondary hover:text-primary'
              }`}
            >
              {period === 'monthly' ? 'Mensal' : 'Anual'}
              {period === 'annual' && (
                <span className="ml-2 px-1.5 py-0.5 bg-emerald-500/20 text-emerald-400 rounded text-[9px]">
                  -20%
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Plan cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {PLANS.map((plan, idx) => {
          const isCurrent = plan.id === currentPlan;
          const planRank = PLAN_RANK[plan.id];
          const isUpgrade = planRank > currentRank;
          const isDowngrade = planRank < currentRank;
          const isPendingTo = billing?.pending_plan === plan.id;
          const price = billingPeriod === 'monthly' ? plan.price_monthly : plan.price_annual;
          const monthlyEquiv = billingPeriod === 'annual' ? Math.round(plan.price_annual / 12) : plan.price_monthly;

          let ctaLabel = 'Começar';
          let ctaAction: 'start' | 'upgrade' | 'downgrade' | null = 'start';
          let ctaDisabled = false;
          let ctaColor = 'bg-bg-primary border border-border text-primary';

          if (isCurrent && hasActiveSubscription) {
            ctaLabel = 'Plano atual';
            ctaDisabled = true;
            ctaAction = null;
          } else if (isPendingTo) {
            ctaLabel = 'Mudança agendada';
            ctaDisabled = true;
            ctaAction = null;
          } else if (isUpgrade && hasActiveSubscription) {
            ctaLabel = 'Upgrade →';
            ctaAction = 'upgrade';
            ctaColor = plan.popular ? 'bg-accent-amethyst text-white' : 'bg-emerald-600 text-white';
          } else if (isDowngrade && hasActiveSubscription) {
            ctaLabel = 'Mudar pra menor';
            ctaAction = 'downgrade';
            ctaColor = 'bg-zinc-700 text-zinc-300';
          } else if (plan.popular) {
            ctaColor = 'bg-accent-amethyst text-white shadow-xl shadow-accent-amethyst/20';
          }

          return (
            <div
              key={plan.id}
              className={`relative p-10 rounded-[40px] border-2 transition-all flex flex-col justify-between ${
                plan.popular
                  ? 'bg-bg-surface border-accent-amethyst shadow-2xl scale-[1.03] z-10'
                  : 'bg-bg-sidebar/30 border-border hover:border-accent-amethyst/30'
              } ${isCurrent ? 'ring-2 ring-emerald-500/50' : ''}`}
            >
              {plan.popular && !isCurrent && (
                <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-accent-amethyst text-white text-[10px] font-black uppercase tracking-widest px-4 py-1.5 rounded-full shadow-lg">
                  Mais Popular
                </div>
              )}
              {isCurrent && (
                <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-emerald-500 text-white text-[10px] font-black uppercase tracking-widest px-4 py-1.5 rounded-full shadow-lg">
                  Plano Atual
                </div>
              )}

              <div className="space-y-6">
                <div>
                  <h3 className="text-xl font-black tracking-tight">{plan.name}</h3>
                  <p className="text-[11px] text-secondary mt-1">{plan.description}</p>
                  <div className="mt-4">
                    <div className="flex items-baseline gap-1">
                      <span className="text-4xl font-black">R${monthlyEquiv}</span>
                      <span className="text-secondary font-bold text-sm">/mês</span>
                    </div>
                    {billingPeriod === 'annual' && (
                      <div className="text-[10px] text-emerald-400 mt-1">
                        R${price} cobrado anualmente · economia de {annualSavings[idx]}%
                      </div>
                    )}
                  </div>
                </div>

                <ul className="space-y-3">
                  {plan.features.map(f => (
                    <li key={f.label} className="flex items-start gap-2.5 text-xs">
                      <div className={`w-4 h-4 mt-0.5 rounded-full flex items-center justify-center flex-shrink-0 ${
                        f.included ? 'bg-accent-amethyst/10' : 'bg-zinc-800/50'
                      }`}>
                        {f.included
                          ? <Check className="w-3 h-3 text-accent-amethyst" />
                          : <XIcon className="w-3 h-3 text-zinc-600" />}
                      </div>
                      <span className={f.included ? 'font-medium' : 'text-secondary line-through'}>
                        {f.label}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>

              <button
                onClick={() => ctaAction && handleAction(plan.id, ctaAction)}
                disabled={ctaDisabled || actionPending === plan.id}
                className={`mt-10 w-full py-4 rounded-2xl text-xs font-black uppercase tracking-widest transition-all flex items-center justify-center gap-2 ${ctaColor} ${
                  ctaDisabled ? 'opacity-50 cursor-not-allowed' : 'hover:scale-[1.02]'
                }`}
              >
                {actionPending === plan.id ? 'Processando...' : ctaLabel}
                {!ctaDisabled && <ArrowRight className="w-4 h-4" />}
              </button>
            </div>
          );
        })}
      </div>

      {/* Usage link */}
      <div className="text-center">
        <Link
          to="/billing/usage"
          className="inline-flex items-center gap-2 text-sm text-secondary hover:text-primary font-bold"
        >
          Ver uso e cotas detalhadas
          <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </div>

      {/* Trust footer */}
      <div className="max-w-3xl mx-auto p-10 bg-bg-sidebar/50 rounded-[40px] border border-border border-dashed text-center space-y-4">
        <div className="flex items-center justify-center gap-3">
          <ShieldCheck className="w-6 h-6 text-secondary/60" />
          <h4 className="font-black">Pagamentos seguros via Stripe</h4>
        </div>
        <p className="text-sm text-secondary font-medium">
          Não armazenamos dados de cartão. Cancelamento a qualquer hora.
          Renovação automática (você pode pausar/cancelar).
        </p>
        <div className="flex items-center justify-center gap-6 pt-2 text-[10px] font-black uppercase tracking-widest text-secondary/60">
          <span>SSL Encrypted</span>
          <span>·</span>
          <span>PCI DSS Compliant</span>
          <span>·</span>
          <span>LGPD-ready</span>
        </div>
      </div>
    </div>
  );
}

function handleBillingError(e: unknown) {
  const body = e instanceof ApiError ? (e.body as { error?: string; message?: string }) : null;
  const known: Record<string, string> = {
    plan_invalid: 'Plano inválido',
    billing_period_invalid: 'Período inválido',
    no_subscription: 'Sem assinatura ativa — comece com checkout',
    not_an_upgrade: 'Esse plano não é um upgrade',
    not_a_downgrade: 'Esse plano não é um downgrade',
    price_not_configured: 'Stripe não configurado',
    stripe_error: 'Erro processando pagamento — tenta novamente',
    no_pending_change: 'Sem mudanças agendadas',
  };
  toast.error(body?.message || known[body?.error || ''] || 'Erro');
}

function CurrentSubscriptionCard({
  billing,
  effective_plan,
  onCancelPending,
  onAbortCancellation,
  onPortal,
}: {
  billing: NonNullable<NonNullable<Awaited<ReturnType<typeof billingApi.getState>>>['billing']>;
  effective_plan: string;
  onCancelPending: () => void;
  onAbortCancellation: () => void;
  onPortal: () => void;
}) {
  const periodEnd = billing.current_period_end
    ? new Date(billing.current_period_end).toLocaleDateString('pt-BR')
    : null;

  return (
    <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-3xl p-6 max-w-3xl mx-auto space-y-4">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-emerald-500/20 flex items-center justify-center">
            <ShieldCheck className="w-6 h-6 text-emerald-500" />
          </div>
          <div>
            <div className="text-xs font-black uppercase tracking-widest text-emerald-500">
              Assinatura Ativa
            </div>
            <div className="text-base font-black mt-0.5">
              {effective_plan.toUpperCase()}{' '}
              {billing.billing_period === 'annual' ? '(anual)' : ''}
              <span className="text-secondary text-sm font-medium ml-2">· R${billing.mrr_brl}/mês</span>
            </div>
          </div>
        </div>
        <button
          onClick={onPortal}
          className="flex items-center gap-2 px-4 py-2 bg-bg-primary border border-border hover:border-accent-amethyst/30 rounded-xl text-[10px] font-black uppercase tracking-widest"
        >
          Gerenciar
          <ExternalLink className="w-3 h-3" />
        </button>
      </div>

      <div className="flex flex-wrap gap-3 text-xs">
        {periodEnd && (
          <span className="flex items-center gap-1.5 px-3 py-1 bg-bg-primary rounded-lg text-secondary">
            <Calendar className="w-3 h-3" />
            Próxima renovação: {periodEnd}
          </span>
        )}
        <span className="flex items-center gap-1.5 px-3 py-1 bg-bg-primary rounded-lg text-secondary capitalize">
          Status: {billing.status || 'unknown'}
        </span>
      </div>

      {billing.cancel_at_period_end && (
        <div className="bg-amber-500/10 border border-amber-500/30 rounded-2xl p-4 flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-500 flex-shrink-0" />
            <div className="text-sm">
              <div className="font-black text-amber-400">Cancelamento agendado</div>
              <div className="text-[11px] text-secondary mt-0.5">
                Sua assinatura expira em {periodEnd}. Você pode reativar antes disso.
              </div>
            </div>
          </div>
          <button
            onClick={onAbortCancellation}
            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-[10px] font-black uppercase tracking-widest"
          >
            Reativar
          </button>
        </div>
      )}

      {billing.pending_plan && (
        <div className="bg-blue-500/10 border border-blue-500/30 rounded-2xl p-4 flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-blue-400 flex-shrink-0" />
            <div className="text-sm">
              <div className="font-black text-blue-400">
                Downgrade pra <strong>{billing.pending_plan.toUpperCase()}</strong> agendado
              </div>
              <div className="text-[11px] text-secondary mt-0.5">
                Será aplicado em{' '}
                {billing.pending_effective_at
                  ? new Date(billing.pending_effective_at).toLocaleDateString('pt-BR')
                  : 'fim do ciclo'}
              </div>
            </div>
          </div>
          <button
            onClick={onCancelPending}
            className="px-4 py-2 bg-bg-primary border border-border hover:border-accent-amethyst/30 rounded-lg text-[10px] font-black uppercase tracking-widest"
          >
            Cancelar
          </button>
        </div>
      )}

      {!billing.cancel_at_period_end && !billing.pending_plan && (
        <div className="flex justify-end">
          <Link
            to="/billing/cancel-subscription"
            className="text-[11px] text-secondary/60 hover:text-red-400 underline-offset-2 hover:underline"
          >
            Cancelar assinatura
          </Link>
        </div>
      )}
    </div>
  );
}
