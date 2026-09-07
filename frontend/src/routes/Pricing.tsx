import { useState } from 'react';
import { Check, Zap, Crown, Rocket, ArrowRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const PLANS = [
  {
    id: 'starter',
    name: 'Essencial',
    price: 49,
    period: '/mês',
    desc: 'Para quem está começando sua jornada digital.',
    icon: Zap,
    gradient: 'from-zinc-800 to-zinc-900',
    border: 'border-zinc-700',
    features: [
      '1 número WhatsApp',
      'Até 100 leads/mês',
      'Tarot Virtual básico',
      'Agendamento online',
      'Link de pagamento',
      'Suporte por email',
    ],
    cta: 'Começar Grátis',
    ctaSub: '14 dias grátis, sem cartão',
    popular: false,
  },
  {
    id: 'pro',
    name: 'Profissional',
    price: 149,
    period: '/mês',
    desc: 'Para empresas e agências que buscam escalar vendas com IA.',
    icon: Crown,
    gradient: 'from-purple-500 to-indigo-500',
    border: 'border-purple-500/40',
    features: [
      'Tudo do Essencial +',
      'Leads ilimitados',
      'Atendimento Multi-Modal com IA',
      'Gerador de Respostas & Copy',
      'Disparos em Massa WhatsApp',
      'Agentes Autônomos de Vendas',
      'Funis Avançados Ilimitados',
      'Integração Completa Meta API',
      'Relatórios de conversão e ROI',
      'Suporte prioritário',
    ],
    cta: 'Começar Grátis',
    ctaSub: '14 dias grátis, cancele quando quiser',
    popular: true,
  },
  {
    id: 'scale',
    name: 'Escala',
    price: 399,
    period: '/mês',
    desc: 'Para grandes operações, múltiplos atendentes e alta escala.',
    icon: Rocket,
    gradient: 'from-amber-500 to-orange-500',
    border: 'border-amber-500/50',
    features: [
      'Tudo do Profissional +',
      'Multi-atendente (até 5)',
      'API completa + webhooks',
      'Trilhas e automações ilimitadas',
      'White-label (sem marca Acássia)',
      'Flow Builder visual avançado',
      'Múltiplos números de WhatsApp',
      'Programa de afiliados',
      'Gestor de conta dedicado',
    ],
    cta: 'Falar com Especialista',
    ctaSub: 'Onboarding personalizado',
    popular: false,
  },
];

export default function Pricing() {
  const navigate = useNavigate();
  const [annual, setAnnual] = useState(false);

  return (
    <div className="min-h-screen bg-black text-white">
      {/* Hero */}
      <section className="relative overflow-hidden pt-20 pb-16 px-6">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-accent-amethyst/10 via-transparent to-transparent" />
        <div className="relative z-10 max-w-4xl mx-auto text-center space-y-6">
          <h1 className="text-5xl md:text-6xl font-black tracking-tight leading-[1.1]">
            Transforme seu dom em um<br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-accent-amethyst to-pink-400">negócio digital</span>
          </h1>
          <p className="text-xl text-zinc-400 max-w-2xl mx-auto">
            A plataforma completa para terapeutas, tarólogos e coaches espirituais. 
            Automatize, escale e fature — sem perder a essência.
          </p>

          <div className="inline-flex items-center bg-zinc-900 rounded-full p-1 border border-zinc-800">
            <button onClick={() => setAnnual(false)}
              className={`px-5 py-2 rounded-full text-sm font-bold transition-all ${!annual ? 'bg-accent-amethyst text-white' : 'text-zinc-400'}`}>
              Mensal
            </button>
            <button onClick={() => setAnnual(true)}
              className={`px-5 py-2 rounded-full text-sm font-bold transition-all ${annual ? 'bg-accent-amethyst text-white' : 'text-zinc-400'}`}>
              Anual <span className="text-emerald-400 text-xs ml-1">-20%</span>
            </button>
          </div>
        </div>
      </section>

      {/* Plans */}
      <section className="max-w-6xl mx-auto px-6 pb-20">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {PLANS.map(plan => {
            const displayPrice = annual ? Math.round(plan.price * 0.8) : plan.price;
            return (
              <div key={plan.id}
                className={`relative rounded-3xl border ${plan.border} bg-zinc-950 p-8 flex flex-col ${plan.popular ? 'ring-2 ring-accent-amethyst shadow-xl shadow-accent-amethyst/10 scale-105' : ''}`}>
                {plan.popular && (
                  <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-gradient-to-r from-accent-amethyst to-pink-500 text-white px-5 py-1.5 rounded-full text-[10px] font-black uppercase tracking-widest">
                    Mais Popular
                  </div>
                )}
                <div className={`w-12 h-12 rounded-2xl bg-gradient-to-br ${plan.gradient} flex items-center justify-center mb-4`}>
                  <plan.icon className="w-6 h-6 text-white" />
                </div>
                <h3 className="text-xl font-black">{plan.name}</h3>
                <p className="text-xs text-zinc-500 mt-1 mb-6">{plan.desc}</p>

                <div className="mb-6">
                  <span className="text-4xl font-black">R${displayPrice}</span>
                  <span className="text-zinc-500 text-sm">{plan.period}</span>
                  {annual && <div className="text-[10px] text-emerald-400 font-bold">Economia de R${(plan.price * 12 - displayPrice * 12).toLocaleString('pt-BR')}/ano</div>}
                </div>

                <ul className="space-y-3 mb-8 flex-1">
                  {plan.features.map(f => (
                    <li key={f} className="flex items-start gap-2 text-sm">
                      <Check className="w-4 h-4 text-accent-amethyst flex-shrink-0 mt-0.5" />
                      <span className="text-zinc-300">{f}</span>
                    </li>
                  ))}
                </ul>

                <a href="/saas/signup"
                  className={`w-full py-4 rounded-2xl font-black uppercase tracking-widest text-sm flex items-center justify-center gap-2 transition-all ${
                    plan.popular
                      ? 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white hover:opacity-90 shadow-lg shadow-purple-600/20'
                      : 'bg-zinc-900 border border-zinc-800 text-white hover:border-zinc-700'
                  }`}>
                  {plan.cta} <ArrowRight className="w-4 h-4" />
                </a>
                <div className="text-center text-[10px] text-zinc-600 mt-2">{plan.ctaSub}</div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Social Proof */}
      <section className="border-t border-zinc-900 py-16 px-6">
        <div className="max-w-4xl mx-auto text-center space-y-8">
          <h2 className="text-3xl font-black">Terapeutas que confiam em nós</h2>
          <div className="grid grid-cols-3 gap-8">
            <div><div className="text-3xl font-black text-accent-amethyst">500+</div><div className="text-xs text-zinc-500">Profissionais ativos</div></div>
            <div><div className="text-3xl font-black text-pink-400">R$2M+</div><div className="text-xs text-zinc-500">Faturados na plataforma</div></div>
            <div><div className="text-3xl font-black text-emerald-400">4.9/5</div><div className="text-xs text-zinc-500">Avaliação média</div></div>
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="border-t border-zinc-900 py-16 px-6">
        <div className="max-w-2xl mx-auto space-y-6">
          <h2 className="text-2xl font-black text-center mb-8">Perguntas Frequentes</h2>
          {[
            { q: 'Preciso de conhecimento técnico?', a: 'Não. O onboarding leva 5 minutos e tudo é visual — sem código.' },
            { q: 'Posso cancelar a qualquer momento?', a: 'Sim, sem multa e sem burocracia. Seus dados ficam guardados por 30 dias.' },
            { q: 'A IA substitui meu trabalho?', a: 'Nunca. A IA amplifica seu dom — atende quando você não pode, gera conteúdo, e mantém seus clientes engajados.' },
            { q: 'Funciona com qual WhatsApp?', a: 'WhatsApp Business API (Cloud API oficial da Meta). Seu número continua o mesmo.' },
          ].map(f => (
            <details key={f.q} className="group bg-zinc-900 border border-zinc-800 rounded-2xl p-5">
              <summary className="font-bold text-sm cursor-pointer list-none flex justify-between items-center">
                {f.q}
                <span className="text-zinc-500 group-open:rotate-45 transition-transform text-xl">+</span>
              </summary>
              <p className="text-sm text-zinc-400 mt-3 leading-relaxed">{f.a}</p>
            </details>
          ))}
        </div>
      </section>
    </div>
  );
}
