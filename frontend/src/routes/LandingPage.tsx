import { useNavigate } from 'react-router-dom';
import { Sparkles, Zap, Shield, ArrowRight, Star, Users, BarChart3, MessageCircle, Wand2, Moon, Flame, Bot } from 'lucide-react';

const FEATURES = [
  { icon: Wand2, title: 'Tarot Virtual IA', desc: 'Leituras automáticas com 78 arcanos, personalizadas para cada lead.' },
  { icon: MessageCircle, title: 'WhatsApp Automatizado', desc: 'Funil completo de vendas rodando 24/7 no WhatsApp Business API.' },
  { icon: BarChart3, title: 'CRM Espiritual', desc: 'Gerencie leads com notas espirituais, signo, progresso e mais.' },
  { icon: Bot, title: 'Coach IA + Oráculo', desc: 'IA treinada em Tarot, Astrologia, Jung e tradições espirituais.' },
  { icon: Flame, title: 'Rituais Personalizados', desc: 'IA gera rituais baseados na lua, humor e objetivos do cliente.' },
  { icon: Moon, title: 'Calendário Espiritual', desc: 'Fases lunares, trânsitos e lembretes automáticos para seus clientes.' },
];

export default function LandingPage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-black text-white overflow-hidden">
      {/* Nav */}
      <nav className="fixed top-0 w-full z-50 bg-black/80 backdrop-blur-xl border-b border-zinc-900/50">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-gradient-to-br from-accent-amethyst to-pink-500 rounded-xl flex items-center justify-center"><Zap className="w-4 h-4 text-white" /></div>
            <span className="text-lg font-black tracking-tight">Meu Mistério</span>
          </div>
          <div className="flex items-center gap-4">
            <button onClick={() => navigate('/pricing')} className="text-sm font-bold text-zinc-400 hover:text-white">Preços</button>
            <button onClick={() => navigate('/saas/login')} className="text-sm font-bold text-zinc-400 hover:text-white">Login</button>
            <button onClick={() => navigate('/saas/register')} className="px-5 py-2 bg-gradient-to-r from-accent-amethyst to-pink-500 text-white rounded-full text-sm font-black hover:opacity-90">Começar Grátis</button>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative pt-32 pb-20 px-6">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-accent-amethyst/15 via-transparent to-transparent" />
        <div className="absolute top-20 left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-accent-amethyst/5 rounded-full blur-3xl" />
        <div className="relative z-10 max-w-4xl mx-auto text-center space-y-8">
          <div className="inline-flex items-center gap-2 bg-accent-amethyst/10 border border-accent-amethyst/20 rounded-full px-5 py-2">
            <Sparkles className="w-4 h-4 text-accent-amethyst" />
            <span className="text-xs font-black uppercase tracking-widest text-accent-amethyst">Plataforma #1 para terapeutas espirituais</span>
          </div>
          <h1 className="text-6xl md:text-7xl font-black tracking-tight leading-[1.05]">
            Transforme seu dom em um{' '}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-accent-amethyst via-pink-400 to-amber-400">negócio digital</span>
          </h1>
          <p className="text-xl text-zinc-400 max-w-2xl mx-auto leading-relaxed">
            A plataforma completa com IA que automatiza seu atendimento no WhatsApp, 
            gera conteúdo para redes sociais e escala suas vendas — 
            sem perder a essência do seu trabalho.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <button onClick={() => navigate('/saas/register')} className="px-8 py-4 bg-gradient-to-r from-accent-amethyst to-pink-500 text-white rounded-2xl font-black text-lg hover:opacity-90 shadow-xl shadow-accent-amethyst/20 flex items-center justify-center gap-2">
              Começar Grátis <ArrowRight className="w-5 h-5" />
            </button>
            <button onClick={() => navigate('/pricing')} className="px-8 py-4 bg-zinc-900 border border-zinc-800 text-white rounded-2xl font-bold text-lg hover:border-zinc-700">
              Ver Planos
            </button>
          </div>
          <p className="text-xs text-zinc-600">14 dias grátis • Sem cartão de crédito • Cancele quando quiser</p>
        </div>
      </section>

      {/* Social Proof */}
      <section className="py-12 border-y border-zinc-900">
        <div className="max-w-4xl mx-auto px-6 flex justify-center gap-12">
          <div className="text-center"><div className="text-3xl font-black text-accent-amethyst">500+</div><div className="text-[10px] font-bold uppercase text-zinc-500 tracking-widest">Profissionais</div></div>
          <div className="text-center"><div className="text-3xl font-black text-pink-400">R$2M+</div><div className="text-[10px] font-bold uppercase text-zinc-500 tracking-widest">Faturados</div></div>
          <div className="text-center"><div className="text-3xl font-black text-emerald-400">50k+</div><div className="text-[10px] font-bold uppercase text-zinc-500 tracking-widest">Leads atendidos</div></div>
          <div className="text-center"><div className="text-3xl font-black text-amber-400">4.9</div><div className="text-[10px] font-bold uppercase text-zinc-500 tracking-widest">Avaliação</div></div>
        </div>
      </section>

      {/* Features */}
      <section className="py-20 px-6">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-black tracking-tight mb-4">Tudo que você precisa.<br/><span className="text-transparent bg-clip-text bg-gradient-to-r from-accent-amethyst to-pink-400">Em um só lugar.</span></h2>
            <p className="text-zinc-500 max-w-lg mx-auto">60+ ferramentas construídas especificamente para quem trabalha com espiritualidade.</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {FEATURES.map(f => (
              <div key={f.title} className="group bg-zinc-950 border border-zinc-900 rounded-2xl p-6 hover:border-accent-amethyst/30 transition-all">
                <div className="w-10 h-10 rounded-xl bg-accent-amethyst/10 flex items-center justify-center mb-4 group-hover:bg-accent-amethyst/20 transition-colors">
                  <f.icon className="w-5 h-5 text-accent-amethyst" />
                </div>
                <h3 className="font-black text-lg mb-2">{f.title}</h3>
                <p className="text-sm text-zinc-500 leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Testimonial */}
      <section className="py-20 px-6 bg-zinc-950 border-y border-zinc-900">
        <div className="max-w-3xl mx-auto text-center space-y-8">
          <div className="flex justify-center gap-1">{[1,2,3,4,5].map(i => <Star key={i} className="w-5 h-5 fill-amber-400 text-amber-400" />)}</div>
          <blockquote className="text-2xl font-bold leading-relaxed italic">
            "Em 3 meses, saí de 20 atendimentos por semana para 80 — sem contratar ninguém. 
            A IA atende no WhatsApp enquanto eu faço as consultas presenciais."
          </blockquote>
          <div className="text-sm text-zinc-400">— Taróloga com 15 anos de experiência, São Paulo</div>
        </div>
      </section>

      {/* CTA Final */}
      <section className="py-20 px-6">
        <div className="max-w-2xl mx-auto text-center space-y-8">
          <h2 className="text-4xl font-black tracking-tight">Pronto para escalar seu dom?</h2>
          <p className="text-zinc-400 text-lg">14 dias grátis. Sem compromisso. Setup em 5 minutos.</p>
          <button onClick={() => navigate('/saas/register')} className="px-10 py-5 bg-gradient-to-r from-accent-amethyst to-pink-500 text-white rounded-2xl font-black text-lg hover:opacity-90 shadow-xl shadow-accent-amethyst/20 flex items-center justify-center gap-2 mx-auto">
            <Sparkles className="w-5 h-5" /> Começar Minha Jornada
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-zinc-900 py-10 px-6">
        <div className="max-w-5xl mx-auto flex flex-col md:flex-row justify-between items-center gap-6">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 bg-gradient-to-br from-accent-amethyst to-pink-500 rounded-lg flex items-center justify-center"><Zap className="w-3 h-3 text-white" /></div>
            <span className="text-sm font-black">Meu Mistério</span>
          </div>
          <div className="flex gap-6 text-xs text-zinc-500">
            <a href="/pricing" className="hover:text-white">Preços</a>
            <a href="/portal/welcome" className="hover:text-white">Portal</a>
            <span>© 2026 Meu Mistério. Todos os direitos reservados.</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
