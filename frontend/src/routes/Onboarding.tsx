import { useEffect, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { ApiError } from '../api/client';
import { 
  Sparkles, 
  ShoppingBag, 
  Layout, 
  MessageCircle, 
  ChevronRight, 
  CheckCircle2,
  Bot,
  ArrowRight,
  ShieldCheck,
  Zap
} from 'lucide-react';
import {
  onboardingApi,
  type OfertaDraft,
  type PersonaDraft,
  type TemplateDraft,
  type WhatsAppDraft,
} from '../api/onboarding';
import { toast } from '../lib/toast';

const STEPS = [
  { id: 'persona', label: 'Persona', icon: Sparkles, desc: 'Defina a alma da sua cigana' },
  { id: 'oferta', label: 'Sua Oferta', icon: ShoppingBag, desc: 'O que você vai vender?' },
  { id: 'template', label: 'Fluxo', icon: Layout, desc: 'Escolha a lógica do atendimento' },
  { id: 'whatsapp', label: 'WhatsApp', icon: MessageCircle, desc: 'Conecte sua conta' },
];

export default function Onboarding() {
  const navigate = useNavigate();
  const { data: status, isLoading: isLoadingStatus } = useQuery({
    queryKey: ['onboarding-status'],
    queryFn: onboardingApi.getStatus,
  });

  const [currentStep, setCurrentStep] = useState<string | null>(null);

  // Sincroniza o step inicial com o backend (sem setState durante render — usa effect).
  useEffect(() => {
    if (!status?.current_step) return;
    if (status.current_step === 'done') {
      navigate('/dashboard');
      return;
    }
    if (currentStep === null) setCurrentStep(status.current_step);
  }, [status, currentStep, navigate]);

  const errMsg = (e: unknown, fallback: string): string => {
    if (e instanceof ApiError) {
      const body = e.body as { error?: string } | null;
      return body?.error || `${fallback} (${e.status})`;
    }
    return (e as Error)?.message || fallback;
  };

  const personaMutation = useMutation({
    mutationFn: onboardingApi.savePersona,
    onSuccess: (res) => setCurrentStep(res.next_step),
    onError: (e) => toast.error(errMsg(e, 'Erro ao salvar persona')),
  });

  const ofertaMutation = useMutation({
    mutationFn: onboardingApi.saveOferta,
    onSuccess: (res) => setCurrentStep(res.next_step),
    onError: (e) => toast.error(errMsg(e, 'Erro ao salvar oferta')),
  });

  const templateMutation = useMutation({
    mutationFn: onboardingApi.saveTemplate,
    onSuccess: (res) => setCurrentStep(res.next_step),
    onError: (e) => toast.error(errMsg(e, 'Erro ao salvar template')),
  });

  const whatsappMutation = useMutation({
    mutationFn: onboardingApi.saveWhatsApp,
    onSuccess: () => {
      toast.success('Onboarding concluído!');
      navigate('/dashboard');
    },
    onError: (e) => toast.error(errMsg(e, 'Erro ao salvar WhatsApp')),
  });

  if (isLoadingStatus || !currentStep) {
    return (
      <div className="min-h-screen bg-bg-primary flex flex-col items-center justify-center p-8">
        <div className="w-16 h-16 border-4 border-accent-amethyst/20 border-t-accent-amethyst rounded-full animate-spin mb-4" />
        <p className="text-secondary font-black uppercase tracking-widest animate-pulse">Iniciando sua jornada...</p>
      </div>
    );
  }

  const stepIndex = STEPS.findIndex(s => s.id === currentStep);

  return (
    <div className="min-h-screen bg-bg-primary text-primary flex overflow-hidden">
      {/* Sidebar de Progresso */}
      <aside className="w-[400px] bg-bg-sidebar border-r border-border p-12 flex flex-col justify-between relative">
        <div className="absolute inset-0 opacity-[0.03] pointer-events-none overflow-hidden">
           <Bot className="w-[600px] h-[600px] absolute -bottom-20 -left-40 rotate-12" />
        </div>
        
        <div className="relative z-10">
          <div className="flex items-center gap-3 mb-12">
            <div className="w-10 h-10 bg-accent-amethyst rounded-2xl flex items-center justify-center shadow-lg shadow-accent-amethyst/20">
              <Zap className="w-6 h-6 text-white" />
            </div>
            <h1 className="text-2xl font-black tracking-tight">Acássia <span className="text-accent-amethyst">Studio</span></h1>
          </div>

          <div className="space-y-8">
            {STEPS.map((s, i) => {
              const isPast = i < stepIndex;
              const isCurrent = i === stepIndex;
              return (
                <div key={s.id} className={`flex gap-6 transition-all duration-500 ${isPast || isCurrent ? 'opacity-100' : 'opacity-30'}`}>
                  <div className="relative flex flex-col items-center">
                    <div className={`w-10 h-10 rounded-2xl flex items-center justify-center transition-all ${
                      isPast ? 'bg-emerald-500 text-white' : 
                      isCurrent ? 'bg-accent-amethyst text-white shadow-xl shadow-accent-amethyst/30' : 
                      'bg-bg-primary border border-border'
                    }`}>
                      {isPast ? <CheckCircle2 className="w-6 h-6" /> : <s.icon className="w-5 h-5" />}
                    </div>
                    {i < STEPS.length - 1 && (
                      <div className={`w-0.5 h-full absolute top-10 mt-2 transition-colors ${isPast ? 'bg-emerald-500' : 'bg-border'}`} />
                    )}
                  </div>
                  <div className="pt-1">
                    <h4 className={`text-sm font-black uppercase tracking-widest ${isCurrent ? 'text-accent-amethyst' : 'text-primary'}`}>
                      {s.label}
                    </h4>
                    <p className="text-xs text-secondary font-medium mt-1">{s.desc}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="relative z-10 p-6 bg-bg-primary/50 border border-border rounded-3xl">
          <p className="text-[11px] font-bold text-secondary leading-relaxed">
            "A tecnologia é a ferramenta, mas a alma da sua cigana é o que converte."
          </p>
        </div>
      </aside>

      {/* Área do Wizard */}
      <main className="flex-1 overflow-y-auto p-12 lg:p-24 bg-gradient-to-br from-bg-primary to-bg-sidebar/20 flex flex-col items-center">
        <div className="max-w-2xl w-full animate-in fade-in slide-in-from-bottom-8 duration-700">
          {currentStep === 'persona' && <PersonaStep onSave={personaMutation.mutate} isPending={personaMutation.isPending} />}
          {currentStep === 'oferta' && <OfertaStep onSave={ofertaMutation.mutate} isPending={ofertaMutation.isPending} />}
          {currentStep === 'template' && <TemplateStep onSave={templateMutation.mutate} isPending={templateMutation.isPending} />}
          {currentStep === 'whatsapp' && <WhatsAppStep onSave={whatsappMutation.mutate} isPending={whatsappMutation.isPending} />}
        </div>
      </main>
    </div>
  );
}

// --- Steps ---

function PersonaStep({ onSave, isPending }: { onSave: (d: PersonaDraft) => void, isPending: boolean }) {
  const [formData, setFormData] = useState({ name: '', tone: 'acolhedor', backstory: '', restrictions: [] as string[] });

  return (
    <div className="space-y-10">
      <div className="space-y-4">
        <h2 className="text-5xl font-black tracking-tighter leading-tight">Quem será o rosto <br/>da sua <span className="text-accent-amethyst">operação?</span></h2>
        <p className="text-lg text-secondary font-medium">Defina a personalidade e o tom de voz da sua atendente virtual.</p>
      </div>

      <div className="space-y-8 bg-bg-surface p-10 rounded-[40px] border border-border shadow-premium">
        <div className="space-y-3">
          <label className="text-[10px] font-black uppercase tracking-[0.2em] text-secondary ml-1">Nome da Cigana / Especialista</label>
          <input 
            type="text"
            value={formData.name}
            onChange={e => setFormData({ ...formData, name: e.target.value })}
            placeholder="Ex: Cigana Esmeralda"
            className="w-full bg-bg-primary border-2 border-border/50 rounded-2xl px-6 py-4 text-sm font-bold focus:border-accent-amethyst transition-all outline-none"
          />
        </div>

        <div className="space-y-3">
          <label className="text-[10px] font-black uppercase tracking-[0.2em] text-secondary ml-1">Tom de Voz</label>
          <div className="grid grid-cols-2 gap-3">
            {['acolhedor', 'direto', 'mistico', 'sedutor'].map(t => (
              <button
                key={t}
                onClick={() => setFormData({ ...formData, tone: t })}
                className={`py-4 rounded-2xl border-2 text-xs font-black uppercase tracking-widest transition-all ${
                  formData.tone === t ? 'bg-accent-amethyst border-accent-amethyst text-white' : 'bg-bg-primary border-border/50 text-secondary hover:border-accent-amethyst/30'
                }`}
              >
                {t}
              </button>
            ))}
          </div>
        </div>

        <div className="space-y-3">
          <label className="text-[10px] font-black uppercase tracking-[0.2em] text-secondary ml-1">História de Origem (Backstory)</label>
          <textarea 
            rows={5}
            value={formData.backstory}
            onChange={e => setFormData({ ...formData, backstory: e.target.value })}
            placeholder="Conte um pouco sobre como ela aprendeu a ler as cartas..."
            className="w-full bg-bg-primary border-2 border-border/50 rounded-2xl px-6 py-4 text-sm font-medium focus:border-accent-amethyst transition-all outline-none resize-none leading-relaxed"
          />
          <p className="text-[9px] text-secondary italic">Mínimo de 20 caracteres.</p>
        </div>

        <button
          onClick={() => onSave(formData)}
          disabled={isPending || formData.name.length < 3 || formData.backstory.length < 20}
          className="w-full py-5 bg-accent-amethyst text-white rounded-3xl text-sm font-black uppercase tracking-[0.2em] shadow-2xl shadow-accent-amethyst/40 hover:scale-[1.02] active:scale-95 transition-all disabled:opacity-30 disabled:scale-100 flex items-center justify-center gap-3"
        >
          Próximo Passo
          <ArrowRight className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
}

function OfertaStep({ onSave, isPending }: { onSave: (d: OfertaDraft) => void, isPending: boolean }) {
  const [formData, setFormData] = useState({ nome: '', preco: '', descricao: '', gateway: 'stripe' });

  return (
    <div className="space-y-10">
      <div className="space-y-4">
        <h2 className="text-5xl font-black tracking-tighter leading-tight">O que seus clientes <br/><span className="text-accent-amethyst">receberão?</span></h2>
        <p className="text-lg text-secondary font-medium">Configure os detalhes do seu produto ou consulta.</p>
      </div>

      <div className="space-y-8 bg-bg-surface p-10 rounded-[40px] border border-border shadow-premium">
        <div className="grid grid-cols-2 gap-6">
          <div className="space-y-3">
            <label className="text-[10px] font-black uppercase tracking-[0.2em] text-secondary ml-1">Nome do Produto</label>
            <input 
              type="text"
              value={formData.nome}
              onChange={e => setFormData({ ...formData, nome: e.target.value })}
              placeholder="Ex: Consulta Completa"
              className="w-full bg-bg-primary border-2 border-border/50 rounded-2xl px-6 py-4 text-sm font-bold focus:border-accent-amethyst transition-all outline-none"
            />
          </div>
          <div className="space-y-3">
            <label className="text-[10px] font-black uppercase tracking-[0.2em] text-secondary ml-1">Preço (R$)</label>
            <input 
              type="text"
              value={formData.preco}
              onChange={e => setFormData({ ...formData, preco: e.target.value })}
              placeholder="49,90"
              className="w-full bg-bg-primary border-2 border-border/50 rounded-2xl px-6 py-4 text-sm font-bold focus:border-accent-amethyst transition-all outline-none"
            />
          </div>
        </div>

        <div className="space-y-3">
          <label className="text-[10px] font-black uppercase tracking-[0.2em] text-secondary ml-1">Descrição Breve</label>
          <textarea 
            rows={3}
            value={formData.descricao}
            onChange={e => setFormData({ ...formData, descricao: e.target.value })}
            placeholder="O que está incluso na oferta?"
            className="w-full bg-bg-primary border-2 border-border/50 rounded-2xl px-6 py-4 text-sm font-medium focus:border-accent-amethyst transition-all outline-none resize-none"
          />
        </div>

        <div className="space-y-3">
          <label className="text-[10px] font-black uppercase tracking-[0.2em] text-secondary ml-1">Gateway de Pagamento</label>
          <div className="grid grid-cols-2 gap-3">
            {['stripe', 'cakto'].map(g => (
              <button
                key={g}
                onClick={() => setFormData({ ...formData, gateway: g })}
                className={`py-4 rounded-2xl border-2 text-xs font-black uppercase tracking-widest transition-all ${
                  formData.gateway === g ? 'bg-accent-amethyst border-accent-amethyst text-white' : 'bg-bg-primary border-border/50 text-secondary'
                }`}
              >
                {g}
              </button>
            ))}
          </div>
        </div>

        <button
          onClick={() => onSave(formData)}
          disabled={isPending || !formData.nome || !formData.preco}
          className="w-full py-5 bg-accent-amethyst text-white rounded-3xl text-sm font-black uppercase tracking-[0.2em] shadow-2xl shadow-accent-amethyst/40 hover:scale-[1.02] active:scale-95 transition-all disabled:opacity-30 disabled:scale-100 flex items-center justify-center gap-3"
        >
          Continuar
          <ArrowRight className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
}

function TemplateStep({ onSave, isPending }: { onSave: (d: TemplateDraft) => void, isPending: boolean }) {
  const [template, setTemplate] = useState('tarot_express');

  return (
    <div className="space-y-10">
      <div className="space-y-4">
        <h2 className="text-5xl font-black tracking-tighter leading-tight">Escolha seu <br/><span className="text-accent-amethyst">Fluxo Inicial</span></h2>
        <p className="text-lg text-secondary font-medium">Selecione um modelo de funil validado para começar.</p>
      </div>

      <div className="grid grid-cols-1 gap-4">
        {[
          { id: 'tarot_express', name: 'Tarot Express', desc: 'Foco em conversão rápida. Ideal para tiragens de 3 cartas.', tag: 'Popular' },
          { id: 'quiromancia_premium', name: 'Quiromancia Premium', desc: 'Fluxo mais longo com maior valor agregado e leitura detalhada.', tag: 'High Ticket' },
          { id: 'em_branco', name: 'Começar do Zero', desc: 'Crie sua própria lógica personalizada usando nosso Flow Builder.', tag: 'Expert' },
        ].map(t => (
          <button
            key={t.id}
            onClick={() => setTemplate(t.id)}
            className={`p-8 rounded-[32px] border-2 text-left transition-all flex items-center justify-between group ${
              template === t.id ? 'bg-accent-amethyst/10 border-accent-amethyst' : 'bg-bg-surface border-border hover:border-accent-amethyst/30'
            }`}
          >
            <div>
              <div className="flex items-center gap-3 mb-2">
                 <h4 className="text-lg font-black tracking-tight">{t.name}</h4>
                 <span className={`text-[8px] font-black uppercase tracking-widest px-2 py-0.5 rounded-full ${template === t.id ? 'bg-accent-amethyst text-white' : 'bg-bg-primary text-secondary'}`}>
                   {t.tag}
                 </span>
              </div>
              <p className="text-sm text-secondary font-medium">{t.desc}</p>
            </div>
            <div className={`w-12 h-12 rounded-2xl flex items-center justify-center transition-all ${template === t.id ? 'bg-accent-amethyst text-white shadow-lg' : 'bg-bg-primary text-secondary'}`}>
               {template === t.id ? <CheckCircle2 className="w-6 h-6" /> : <ChevronRight className="w-6 h-6" />}
            </div>
          </button>
        ))}
      </div>

      <button
        onClick={() => onSave({ template })}
        disabled={isPending}
        className="w-full py-5 bg-accent-amethyst text-white rounded-3xl text-sm font-black uppercase tracking-[0.2em] shadow-2xl shadow-accent-amethyst/40 hover:scale-[1.02] active:scale-95 transition-all flex items-center justify-center gap-3 mt-8"
      >
        Configurar Fluxo
        <ArrowRight className="w-5 h-5" />
      </button>
    </div>
  );
}

function WhatsAppStep({ onSave, isPending }: { onSave: (d: WhatsAppDraft) => void, isPending: boolean }) {
  const [formData, setFormData] = useState({ phone_number_id: '', waba_id: '', access_token: '' });

  return (
    <div className="space-y-10">
      <div className="space-y-4">
        <h2 className="text-5xl font-black tracking-tighter leading-tight">Conecte sua conta <br/><span className="text-accent-amethyst">WhatsApp</span></h2>
        <p className="text-lg text-secondary font-medium">Insira as credenciais da API da Meta para ativar o bot.</p>
      </div>

      <div className="bg-amber-500/10 border border-amber-500/20 p-6 rounded-3xl flex gap-4">
         <div className="w-10 h-10 rounded-2xl bg-amber-500/20 flex items-center justify-center flex-shrink-0">
            <ShieldCheck className="w-6 h-6 text-amber-500" />
         </div>
         <p className="text-xs text-amber-600/90 leading-relaxed font-medium">
            Seus dados de conexão são criptografados e nunca compartilhados. <br/>
            Precisa de ajuda para encontrar essas chaves? <a href="#" className="underline font-bold">Veja o tutorial.</a>
         </p>
      </div>

      <div className="space-y-8 bg-bg-surface p-10 rounded-[40px] border border-border shadow-premium">
        <div className="grid grid-cols-2 gap-6">
          <div className="space-y-3">
            <label className="text-[10px] font-black uppercase tracking-[0.2em] text-secondary ml-1">Phone Number ID</label>
            <input 
              type="text"
              value={formData.phone_number_id}
              onChange={e => setFormData({ ...formData, phone_number_id: e.target.value })}
              placeholder="Ex: 123456789"
              className="w-full bg-bg-primary border-2 border-border/50 rounded-2xl px-6 py-4 text-sm font-bold focus:border-accent-amethyst transition-all outline-none"
            />
          </div>
          <div className="space-y-3">
            <label className="text-[10px] font-black uppercase tracking-[0.2em] text-secondary ml-1">WABA ID</label>
            <input 
              type="text"
              value={formData.waba_id}
              onChange={e => setFormData({ ...formData, waba_id: e.target.value })}
              placeholder="Ex: 987654321"
              className="w-full bg-bg-primary border-2 border-border/50 rounded-2xl px-6 py-4 text-sm font-bold focus:border-accent-amethyst transition-all outline-none"
            />
          </div>
        </div>

        <div className="space-y-3">
          <label className="text-[10px] font-black uppercase tracking-[0.2em] text-secondary ml-1">System Access Token (Meta)</label>
          <textarea 
            rows={4}
            value={formData.access_token}
            onChange={e => setFormData({ ...formData, access_token: e.target.value })}
            placeholder="EAAB..."
            className="w-full bg-bg-primary border-2 border-border/50 rounded-2xl px-6 py-4 text-sm font-mono break-all focus:border-accent-amethyst transition-all outline-none resize-none"
          />
        </div>

        <button
          onClick={() => onSave(formData)}
          disabled={isPending || !formData.phone_number_id || !formData.access_token}
          className="w-full py-5 bg-accent-amethyst text-white rounded-3xl text-sm font-black uppercase tracking-[0.2em] shadow-2xl shadow-accent-amethyst/40 hover:scale-[1.02] active:scale-95 transition-all flex items-center justify-center gap-3 mt-4"
        >
          {isPending ? 'Finalizando...' : 'Concluir Configuração'}
          <ArrowRight className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
}
