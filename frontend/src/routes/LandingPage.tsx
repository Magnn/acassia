import { useNavigate } from 'react-router-dom';
import { Sparkles, Zap, Shield, ArrowRight, Star, Users, BarChart3, MessageCircle, Bot, Share2, Workflow, Clock, CheckCircle2 } from 'lucide-react';

const FEATURES = [
  { icon: Workflow, title: 'Visual Flow Builder', desc: 'Crie funis conversacionais de alta conversão arrastando e soltando blocos, sem programar.' },
  { icon: MessageCircle, title: 'WhatsApp Business API', desc: 'Atendimento oficial 24/7 com suporte a texto, áudio natural, botões, imagens e PIX.' },
  { icon: Bot, title: 'IA Vendedora Humanizada', desc: 'Atendimento inteligente que qualifica leads, quebra objeções e fecha vendas automaticamente.' },
  { icon: BarChart3, title: 'CRM & Pipeline Kanban', desc: 'Gerencie leads em tempo real com tags dinâmicas, score de interesse e transbordo humano.' },
  { icon: Share2, title: 'Meta Conversions API (CAPI)', desc: 'Envie eventos de Purchase e Lead direto para o Pixel do Facebook e otimize suas campanhas.' },
  { icon: Clock, title: 'Agendamento & Broadcast', desc: 'Disparos em massa agendados com anti-bloqueio e calendário interativo embutido no chat.' },
];

export default function LandingPage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-black text-white overflow-hidden">
      {/* Nav */}
      <nav className="fixed top-0 w-full z-50 bg-black/80 backdrop-blur-xl border-b border-zinc-900/50">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 bg-gradient-to-br from-purple-600 to-indigo-600 rounded-xl flex items-center justify-center shadow-lg shadow-purple-600/30">
              <Zap className="w-4 h-4 text-white" />
            </div>
            <span className="text-lg font-black tracking-tight bg-gradient-to-r from-white to-zinc-400 bg-clip-text text-transparent">Acássia</span>
          </div>
          <div className="flex items-center gap-4">
            <button onClick={() => navigate('/pricing')} className="text-sm font-bold text-zinc-400 hover:text-white transition-colors">Preços</button>
            <button onClick={() => navigate('/saas/login')} className="text-sm font-bold text-zinc-400 hover:text-white transition-colors">Login</button>
            <button onClick={() => navigate('/saas/register')} className="px-5 py-2 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-full text-sm font-black hover:opacity-95 shadow-md shadow-purple-600/20 transition-all">Começar Grátis</button>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative pt-36 pb-20 px-6">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-purple-600/20 via-transparent to-transparent" />
        <div className="absolute top-20 left-1/2 -translate-x-1/2 w-[700px] h-[700px] bg-purple-600/10 rounded-full blur-3xl pointer-events-none" />
        <div className="relative z-10 max-w-4xl mx-auto text-center space-y-8">
          <div className="inline-flex items-center gap-2 bg-purple-600/10 border border-purple-500/20 rounded-full px-5 py-2">
            <Sparkles className="w-4 h-4 text-purple-400" />
            <span className="text-xs font-black uppercase tracking-widest text-purple-300">Plataforma de Funis e IA para WhatsApp</span>
          </div>
          <h1 className="text-5xl sm:text-6xl md:text-7xl font-black tracking-tight leading-[1.08]">
            Automatize suas vendas no WhatsApp com{' '}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-400 via-indigo-300 to-pink-400">IA de Verdade</span>
          </h1>
          <p className="text-lg sm:text-xl text-zinc-400 max-w-2xl mx-auto leading-relaxed">
            A plataforma completa para qualquer empresa criar funis interativos, qualificar clientes, 
            recuperar carrinhos abandonados e vender 24 horas por dia no piloto automático.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center pt-2">
            <button onClick={() => navigate('/saas/register')} className="px-8 py-4 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-2xl font-black text-base sm:text-lg hover:opacity-90 shadow-xl shadow-purple-600/25 flex items-center justify-center gap-2 transition-all">
              Criar Conta Gratuita <ArrowRight className="w-5 h-5" />
            </button>
            <button onClick={() => navigate('/pricing')} className="px-8 py-4 bg-zinc-900/80 border border-zinc-800 hover:border-zinc-700 text-white rounded-2xl font-bold text-base sm:text-lg transition-all">
              Conhecer Planos
            </button>
          </div>
          <div className="flex items-center justify-center gap-6 text-xs text-zinc-500 pt-2">
            <span className="flex items-center gap-1.5"><CheckCircle2 className="w-4 h-4 text-emerald-500" /> 14 dias grátis</span>
            <span className="flex items-center gap-1.5"><CheckCircle2 className="w-4 h-4 text-emerald-500" /> Sem cartão de crédito</span>
            <span className="flex items-center gap-1.5"><CheckCircle2 className="w-4 h-4 text-emerald-500" /> Setup em 3 minutos</span>
          </div>
        </div>
      </section>

      {/* Social Proof */}
      <section className="py-12 border-y border-zinc-900 bg-zinc-950/40">
        <div className="max-w-4xl mx-auto px-6 grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
          <div><div className="text-3xl sm:text-4xl font-black text-purple-400">98%</div><div className="text-[11px] font-bold uppercase text-zinc-500 tracking-widest mt-1">Taxa de Abertura</div></div>
          <div><div className="text-3xl sm:text-4xl font-black text-indigo-400">3.4x</div><div className="text-[11px] font-bold uppercase text-zinc-500 tracking-widest mt-1">Mais Conversão</div></div>
          <div><div className="text-3xl sm:text-4xl font-black text-emerald-400">24/7</div><div className="text-[11px] font-bold uppercase text-zinc-500 tracking-widest mt-1">Atendimento Ativo</div></div>
          <div><div className="text-3xl sm:text-4xl font-black text-pink-400">0s</div><div className="text-[11px] font-bold uppercase text-zinc-500 tracking-widest mt-1">Tempo de Espera</div></div>
        </div>
      </section>

      {/* Features */}
      <section className="py-24 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16 space-y-3">
            <h2 className="text-3xl sm:text-4xl md:text-5xl font-black tracking-tight">
              Tudo o que sua empresa precisa para <br className="hidden sm:inline" />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-400 via-indigo-300 to-pink-400">vender mais pelo WhatsApp</span>
            </h2>
            <p className="text-zinc-400 max-w-xl mx-auto text-sm sm:text-base">Construído para e-commerces, infoprodutores, clínicas, imobiliárias e prestadores de serviços.</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {FEATURES.map(f => (
              <div key={f.title} className="group bg-zinc-950 border border-zinc-900 rounded-3xl p-7 hover:border-purple-500/40 hover:bg-zinc-900/30 transition-all flex flex-col justify-between">
                <div>
                  <div className="w-12 h-12 rounded-2xl bg-purple-600/10 flex items-center justify-center mb-5 group-hover:bg-purple-600/20 text-purple-400 transition-colors">
                    <f.icon className="w-6 h-6" />
                  </div>
                  <h3 className="font-black text-xl mb-2 text-white">{f.title}</h3>
                  <p className="text-sm text-zinc-400 leading-relaxed">{f.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Testimonial */}
      <section className="py-20 px-6 bg-zinc-950/60 border-y border-zinc-900">
        <div className="max-w-3xl mx-auto text-center space-y-6">
          <div className="flex justify-center gap-1.5">{[1,2,3,4,5].map(i => <Star key={i} className="w-5 h-5 fill-amber-400 text-amber-400" />)}</div>
          <blockquote className="text-xl sm:text-2xl font-bold leading-relaxed text-zinc-200">
            "Configuramos nosso funil de vendas em uma tarde. Na mesma semana, a IA fechou mais de 45 pedidos de forma totalmente automática enquanto a equipe focava na operação."
          </blockquote>
          <div className="text-sm text-zinc-400 font-medium">— Diretor Comercial, E-commerce B2C</div>
        </div>
      </section>

      {/* CTA Final */}
      <section className="py-24 px-6 text-center">
        <div className="max-w-3xl mx-auto space-y-8">
          <h2 className="text-4xl sm:text-5xl font-black tracking-tight">Pronto para transformar seu WhatsApp em uma máquina de vendas?</h2>
          <p className="text-zinc-400 text-base sm:text-lg max-w-xl mx-auto">Junte-se a milhares de negócios que escalam vendas com funis inteligentes e IA 24/7.</p>
          <button onClick={() => navigate('/saas/register')} className="px-10 py-5 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-2xl font-black text-lg hover:opacity-90 shadow-xl shadow-purple-600/25 flex items-center justify-center gap-2 mx-auto transition-all">
            <Zap className="w-5 h-5" /> Começar Agora Gratuitamente
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-zinc-900 py-10 px-6 bg-black">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row justify-between items-center gap-6">
          <div className="flex items-center gap-2.5">
            <div className="w-6 h-6 bg-gradient-to-br from-purple-600 to-indigo-600 rounded-lg flex items-center justify-center shadow-sm"><Zap className="w-3.5 h-3.5 text-white" /></div>
            <span className="text-sm font-black text-white">Acássia</span>
          </div>
          <div className="flex gap-6 text-xs text-zinc-500">
            <a href="/pricing" className="hover:text-white transition-colors">Planos & Preços</a>
            <a href="/api/docs" className="hover:text-white transition-colors">Documentação API</a>
            <span>© 2026 Acássia. Todos os direitos reservados.</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

