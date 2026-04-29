import { useQuery, useMutation } from '@tanstack/react-query';
import {
  ArrowRight,
  Check,
  CreditCard,
  ExternalLink,
  ShieldCheck,
} from 'lucide-react';
import { billingApi } from '../api/billing';
import { toast } from '../lib/toast';

const PLANS = [
  { id: 'starter', name: 'Starter', price: '97', features: ['Até 500 leads/mês', '1 Agente IA', 'Suporte por Email'] },
  { id: 'pro', name: 'Pro', price: '197', features: ['Leads Ilimitados', '3 Agentes IA', 'Suporte Prioritário', 'Remover Branding'], popular: true },
  { id: 'enterprise', name: 'Enterprise', price: '497', features: ['Tudo do Pro', 'Agentes Ilimitados', 'API de Integração', 'Consultoria de Fluxo'] },
];

export default function Billing() {
  const { data: billing, isLoading } = useQuery({
    queryKey: ['billing-plans'],
    queryFn: billingApi.getPlans,
  });

  const checkoutMutation = useMutation({
    mutationFn: (plan: string) => billingApi.startCheckout(plan),
    onSuccess: (res) => {
      if (res?.url) window.location.href = res.url;
      else toast.error(res?.error || 'Falha ao obter URL de checkout.');
    },
    onError: (e: Error) => toast.error(`Erro ao iniciar checkout: ${e.message}`),
  });

  const portalMutation = useMutation({
    mutationFn: billingApi.openPortal,
    onSuccess: (res) => {
      if (res?.url) window.location.href = res.url;
      else toast.error(res?.error || 'Falha ao abrir portal.');
    },
    onError: (e: Error) => toast.error(`Erro ao abrir portal: ${e.message}`),
  });

  if (isLoading) return <div className="p-8 text-center animate-pulse">Carregando planos...</div>;

  return (
    <div className="p-10 max-w-7xl mx-auto space-y-12">
      <div className="text-center space-y-4">
        <h2 className="text-4xl font-black tracking-tight">Sua Assinatura <span className="text-accent-amethyst">Acássia</span></h2>
        <p className="text-secondary font-medium max-w-2xl mx-auto">
          Escolha o plano ideal para escalar seu atendimento espiritual e gerenciar seus leads com inteligência.
        </p>
      </div>

      {billing?.current_status && (
        <div className="bg-emerald-500/10 border border-emerald-500/20 p-6 rounded-3xl flex items-center justify-between max-w-3xl mx-auto shadow-sm">
           <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-2xl bg-emerald-500/20 flex items-center justify-center">
                 <ShieldCheck className="w-6 h-6 text-emerald-500" />
              </div>
              <div>
                 <div className="text-xs font-black uppercase tracking-widest text-emerald-600">Assinatura Ativa</div>
                 <div className="text-sm font-bold text-primary">Status: {billing.current_status}</div>
              </div>
           </div>
           <button 
            onClick={() => portalMutation.mutate()}
            className="flex items-center gap-2 px-5 py-2.5 bg-bg-primary border border-border hover:border-accent-amethyst/30 rounded-2xl text-[10px] font-black uppercase tracking-widest transition-all"
           >
             Gerenciar Assinatura
             <ExternalLink className="w-3.5 h-3.5" />
           </button>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {PLANS.map((plan) => (
          <div 
            key={plan.id}
            className={`relative p-10 rounded-[40px] border-2 transition-all flex flex-col justify-between ${
              plan.popular ? 'bg-bg-surface border-accent-amethyst shadow-2xl scale-105 z-10' : 'bg-bg-sidebar/30 border-border hover:border-accent-amethyst/30'
            }`}
          >
            {plan.popular && (
              <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-accent-amethyst text-white text-[10px] font-black uppercase tracking-widest px-4 py-1.5 rounded-full shadow-lg">
                Mais Popular
              </div>
            )}
            
            <div className="space-y-6">
              <div>
                <h3 className="text-xl font-black tracking-tight">{plan.name}</h3>
                <div className="mt-4 flex items-baseline gap-1">
                  <span className="text-4xl font-black">R${plan.price}</span>
                  <span className="text-secondary font-bold text-sm">/mês</span>
                </div>
              </div>

              <ul className="space-y-4">
                {plan.features.map(f => (
                  <li key={f} className="flex items-center gap-3 text-xs font-medium">
                    <div className="w-5 h-5 rounded-full bg-accent-amethyst/10 flex items-center justify-center flex-shrink-0">
                       <Check className="w-3 h-3 text-accent-amethyst" />
                    </div>
                    {f}
                  </li>
                ))}
              </ul>
            </div>

            <button
              onClick={() => checkoutMutation.mutate(plan.id)}
              disabled={checkoutMutation.isPending}
              className={`mt-10 w-full py-4 rounded-2xl text-xs font-black uppercase tracking-widest transition-all flex items-center justify-center gap-2 ${
                plan.popular 
                  ? 'bg-accent-amethyst text-white shadow-xl shadow-accent-amethyst/20 hover:scale-[1.02]' 
                  : 'bg-bg-primary border border-border text-primary hover:border-accent-amethyst/30'
              }`}
            >
              Começar Agora
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        ))}
      </div>

      <div className="max-w-3xl mx-auto p-10 bg-bg-sidebar/50 rounded-[40px] border border-border border-dashed text-center space-y-6">
         <div className="w-16 h-16 bg-bg-primary rounded-3xl border border-border flex items-center justify-center mx-auto shadow-sm">
            <CreditCard className="w-8 h-8 text-secondary/40" />
         </div>
         <div className="space-y-2">
            <h4 className="font-black text-lg">Segurança em primeiro lugar</h4>
            <p className="text-sm text-secondary font-medium px-10">
               Utilizamos o **Stripe** para processar todos os pagamentos. Não armazenamos seus dados de cartão em nossos servidores.
            </p>
         </div>
         <div className="flex items-center justify-center gap-8 pt-4">
            <div className="flex items-center gap-2 opacity-40">
               <ShieldCheck className="w-4 h-4" />
               <span className="text-[10px] font-black uppercase tracking-widest">SSL Encrypted</span>
            </div>
            <div className="flex items-center gap-2 opacity-40">
               <Check className="w-4 h-4" />
               <span className="text-[10px] font-black uppercase tracking-widest">Cancelamento a qualquer hora</span>
            </div>
         </div>
      </div>
    </div>
  );
}
