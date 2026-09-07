import { useEffect, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { ApiError } from '../api/client';
import {
  Sparkles,
  ShoppingBag,
  Layout,
  MessageCircle,
  CheckCircle2,
  Bot,
  ArrowRight,
  ShieldCheck,
  Zap,
  Copy,
  ExternalLink,
  Inbox,
  Eye,
  EyeOff,
  Shield,
  XCircle,
  AlertTriangle,
} from 'lucide-react';
import {
  onboardingApi,
  type OfertaDraft,
  type PersonaDraft,
  type TemplateDraft,
  type WhatsAppStepResult,
} from '../api/onboarding';
import { integrationsApi } from '../api/integrations';
import { templatesApi, type FlowTemplate } from '../api/templates';
import { toast } from '../lib/toast';
import { track } from '../lib/analytics';

const STEPS = [
  { id: 'persona', label: 'Seu Atendimento', icon: Sparkles, desc: 'Dê vida à sua atendente que vende 24/7' },
  { id: 'oferta', label: 'Seu Produto', icon: ShoppingBag, desc: 'Monte o que vai gerar o primeiro "sim"' },
  { id: 'template', label: 'Seu Funil', icon: Layout, desc: 'Escolha e adapte seu modelo de atendimento' },
  { id: 'whatsapp', label: 'WhatsApp', icon: MessageCircle, desc: 'Conecte e teste sua primeira conversa' },
];

export default function Onboarding() {
  const navigate = useNavigate();
  const { data: status, isLoading: isLoadingStatus, error: statusError } = useQuery({
    queryKey: ['onboarding-status'],
    queryFn: onboardingApi.getStatus,
    retry: false,
  });

  useEffect(() => {
    if (statusError instanceof ApiError && statusError.status === 401) {
      window.location.href = '/saas/login?next=' + encodeURIComponent('/builder/onboarding');
    }
  }, [statusError]);

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
    onSuccess: (res) => {
      track('onboarding_step_completed', { step: 'persona', next: res.next_step });
      setCurrentStep(res.next_step);
    },
    onError: (e) => toast.error(errMsg(e, 'Erro ao salvar persona')),
  });

  const ofertaMutation = useMutation({
    mutationFn: onboardingApi.saveOferta,
    onSuccess: (res) => {
      track('onboarding_step_completed', { step: 'oferta', next: res.next_step });
      setCurrentStep(res.next_step);
    },
    onError: (e) => toast.error(errMsg(e, 'Erro ao salvar oferta')),
  });

  const templateMutation = useMutation({
    mutationFn: onboardingApi.saveTemplate,
    onSuccess: (res) => {
      track('onboarding_step_completed', { step: 'template', next: res.next_step });
      setCurrentStep(res.next_step);
    },
    onError: (e) => toast.error(errMsg(e, 'Erro ao salvar template')),
  });

  if (statusError) {
    return <div role="alert" className="p-12 text-center space-y-4">
      <p>Não foi possível carregar sua configuração.</p>
      <button onClick={() => window.location.reload()} className="underline">Tentar novamente</button>
    </div>;
  }

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
            <h1 className="text-2xl font-black tracking-tight">Meu Mistério <span className="text-accent-amethyst">Studio</span></h1>
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
            Configure o atendimento, teste a conversa e acompanhe os resultados do seu negócio.
          </p>
        </div>
      </aside>

      {/* Área do Wizard */}
      <main className="flex-1 overflow-y-auto p-12 lg:p-24 bg-gradient-to-br from-bg-primary to-bg-sidebar/20 flex flex-col items-center">
        <div className="max-w-2xl w-full animate-in fade-in slide-in-from-bottom-8 duration-700">
          {currentStep === 'persona' && <PersonaStep onSave={personaMutation.mutate} isPending={personaMutation.isPending} />}
          {currentStep === 'oferta' && <OfertaStep onSave={ofertaMutation.mutate} isPending={ofertaMutation.isPending} />}
          {currentStep === 'template' && <TemplateStep onSave={templateMutation.mutate} isPending={templateMutation.isPending} />}
          {currentStep === 'whatsapp' && <WhatsAppStep />}
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
        <h2 className="text-5xl font-black tracking-tighter leading-tight">Dê vida à sua <br/><span className="text-accent-amethyst">atendente digital</span></h2>
        <p className="text-lg text-secondary font-medium">Defina como seu negócio conversa com clientes, apresenta ofertas e encaminha dúvidas para sua equipe.</p>
      </div>

      <div className="space-y-8 bg-bg-surface p-10 rounded-[40px] border border-border shadow-premium">
        <div className="space-y-3">
          <label className="text-[10px] font-black uppercase tracking-[0.2em] text-secondary ml-1">Nome do atendente / Especialista</label>
          <input 
            type="text"
            value={formData.name}
            onChange={e => setFormData({ ...formData, name: e.target.value })}
            placeholder="Ex: Ana, assistente da sua empresa"
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
          <label className="text-[10px] font-black uppercase tracking-[0.2em] text-secondary ml-1">Sobre o negócio e o atendimento</label>
          <textarea 
            rows={5}
            value={formData.backstory}
            onChange={e => setFormData({ ...formData, backstory: e.target.value })}
            placeholder="Descreva seu negócio, público, diferenciais e como o atendente deve ajudar. Para a Cigana, inclua sua história e estilo de leitura."
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
        <h2 className="text-5xl font-black tracking-tighter leading-tight">Monte o produto que vai<br/><span className="text-accent-amethyst">gerar o primeiro "sim"</span></h2>
        <p className="text-lg text-secondary font-medium">Defina o que você entrega, quanto custa, e como recebe. Simples assim.</p>
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

const CATEGORY_BADGE: Record<string, { label: string; color: string }> = {
  amor: { label: 'Amor', color: 'bg-rose-500/20 text-rose-300' },
  premium: { label: 'High Ticket', color: 'bg-amber-500/20 text-amber-300' },
  astrologia: { label: 'Astrologia', color: 'bg-purple-500/20 text-purple-300' },
  recuperacao: { label: 'Win-back', color: 'bg-blue-500/20 text-blue-300' },
};

function TemplateStep({ onSave, isPending }: { onSave: (d: TemplateDraft) => void, isPending: boolean }) {
  const [selectedId, setSelectedId] = useState<string>('em_branco');
  const [previewing, setPreviewing] = useState<FlowTemplate | null>(null);

  const { data, isLoading, error: templatesError } = useQuery({
    queryKey: ['onboarding-templates'],
    queryFn: () => templatesApi.list(),
  });

  const items = data?.templates ?? [];

  return (
    <div className="space-y-10">
      <div className="space-y-4">
        <h2 className="text-5xl font-black tracking-tighter leading-tight">
          Monte sua <br/>
          <span className="text-accent-amethyst">jornada de atendimento</span>
        </h2>
        <p className="text-lg text-secondary font-medium">
          Escolha um modelo, ajuste as mensagens e teste antes de publicar.
        </p>
      </div>

      {templatesError && <p role="alert" className="text-sm text-secondary">Não foi possível carregar os kits do catálogo. Você pode usar o modelo comercial ou começar em branco.</p>}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 animate-pulse">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-48 bg-bg-surface rounded-3xl" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <button type="button" aria-pressed={selectedId === 'atendimento_comercial'}
            onClick={() => setSelectedId('atendimento_comercial')}
            className={`p-6 rounded-3xl border-2 text-left ${selectedId === 'atendimento_comercial' ? 'border-accent-amethyst bg-accent-amethyst/10' : 'border-border bg-bg-surface'}`}>
            <span className="block text-lg font-bold">Atendimento comercial inicial</span>
            <span className="block mt-2 text-sm text-secondary">Receba o cliente, entenda sua necessidade, apresente a oferta cadastrada e encaminhe dúvidas para a equipe. Adapte para seu negócio no editor.</span>
            <span className="block mt-3 text-xs font-bold">{selectedId === 'atendimento_comercial' ? 'Selecionado' : 'Selecionar modelo'}</span>
          </button>
          {items.map((t) => {
            const badge = CATEGORY_BADGE[t.category || ''] ?? { label: 'Kit', color: 'bg-bg-primary text-secondary' };
            const isSelected = selectedId === t.id;
            return (
              <div
                key={t.id}
                onClick={() => setSelectedId(t.id)}
                className={`p-6 rounded-[24px] border-2 cursor-pointer transition-all ${
                  isSelected
                    ? 'bg-accent-amethyst/10 border-accent-amethyst'
                    : 'bg-bg-surface border-border hover:border-accent-amethyst/30'
                }`}
              >
                <div className="flex items-start justify-between mb-3">
                  <h4 className="text-lg font-black tracking-tight">{t.name}</h4>
                  <span className={`text-[9px] font-black uppercase tracking-widest px-2 py-0.5 rounded ${badge.color}`}>
                    {badge.label}
                  </span>
                </div>
                <p className="text-xs text-secondary leading-relaxed mb-4 line-clamp-3">
                  {t.description}
                </p>
                <div className="flex items-center justify-between text-[11px] text-secondary mb-3">
                  <span>{t.node_count} nós</span>
                  {t.ticket_brl_avg > 0 && (
                    <span className="font-mono">R${t.ticket_brl_avg}</span>
                  )}
                  {t.usage_count > 0 && (
                    <span>{t.usage_count} usos</span>
                  )}
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={(e) => { e.stopPropagation(); setPreviewing(t); }}
                    className="flex-1 px-3 py-1.5 bg-bg-primary border border-border hover:border-accent-amethyst/30 rounded-lg text-[11px] font-bold"
                  >
                    Preview
                  </button>
                  <span
                    className={`flex items-center justify-center px-3 rounded-lg text-[11px] font-black uppercase tracking-widest ${
                      isSelected
                        ? 'bg-accent-amethyst text-white'
                        : 'bg-bg-primary text-secondary'
                    }`}
                  >
                    {isSelected ? '✓ Selecionado' : 'Selecionar'}
                  </span>
                </div>
              </div>
            );
          })}

          {/* "Começar do zero" — opção sempre disponível */}
          <div
            onClick={() => setSelectedId('em_branco')}
            className={`p-6 rounded-[24px] border-2 cursor-pointer transition-all ${
              selectedId === 'em_branco'
                ? 'bg-accent-amethyst/10 border-accent-amethyst'
                : 'bg-bg-surface border-dashed border-border hover:border-accent-amethyst/30'
            }`}
          >
            <div className="flex items-start justify-between mb-3">
              <h4 className="text-lg font-black tracking-tight">Começar do zero</h4>
              <span className="text-[9px] font-black uppercase tracking-widest px-2 py-0.5 rounded bg-bg-primary text-secondary">
                Expert
              </span>
            </div>
            <p className="text-xs text-secondary leading-relaxed mb-4">
              Crie sua própria lógica personalizada usando nosso Flow Builder.
            </p>
            <span
              className={`block text-center py-1.5 rounded-lg text-[11px] font-black uppercase tracking-widest ${
                selectedId === 'em_branco'
                  ? 'bg-accent-amethyst text-white'
                  : 'bg-bg-primary text-secondary'
              }`}
            >
              {selectedId === 'em_branco' ? '✓ Selecionado' : 'Selecionar'}
            </span>
          </div>
        </div>
      )}

      <button
        onClick={() => onSave({ template: selectedId })}
        disabled={isPending}
        className="w-full py-5 bg-accent-amethyst text-white rounded-3xl text-sm font-black uppercase tracking-[0.2em] shadow-2xl shadow-accent-amethyst/40 hover:scale-[1.02] active:scale-95 transition-all flex items-center justify-center gap-3 mt-8 disabled:opacity-30 disabled:scale-100"
      >
        {isPending ? 'Aplicando…' : 'Aplicar este kit'}
        <ArrowRight className="w-5 h-5" />
      </button>

      {previewing && (
        <KitPreviewModal
          template={previewing}
          onClose={() => setPreviewing(null)}
          onUse={() => {
            setSelectedId(previewing.id);
            setPreviewing(null);
          }}
        />
      )}
    </div>
  );
}


function KitPreviewModal({
  template, onClose, onUse,
}: {
  template: FlowTemplate;
  onClose: () => void;
  onUse: () => void;
}) {
  const { data: detail, isLoading } = useQuery({
    queryKey: ['onboarding-template-detail', template.id],
    queryFn: () => templatesApi.get(template.id),
  });

  type PreviewNode = { id: string; type: string; label?: string; text?: string; config?: { body?: string; content_text?: string; question?: string } };
  const document = detail?.blueprint_json as { graph?: { nodes?: PreviewNode[] }; nodes?: PreviewNode[] } | undefined;
  const nodes = document?.graph?.nodes ?? document?.nodes ?? [];

  return (
    <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-6">
      <div className="bg-bg-surface border border-border rounded-3xl max-w-2xl w-full max-h-[80vh] overflow-hidden flex flex-col">
        <div className="p-6 border-b border-border flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 className="text-xl font-black tracking-tight truncate">{template.name}</h2>
            <p className="text-xs text-secondary mt-1 line-clamp-2">{template.description}</p>
          </div>
          <button aria-label="Fechar prévia" onClick={onClose} className="text-secondary hover:text-primary text-2xl leading-none flex-shrink-0">
            ×
          </button>
        </div>
        <div className="p-6 overflow-y-auto flex-1 space-y-3">
          {isLoading ? (
            <div className="text-center text-secondary text-sm py-8">Carregando preview…</div>
          ) : (
            <>
              <h3 className="text-[10px] font-black uppercase tracking-widest text-secondary">
                {nodes.length} nós no funil
              </h3>
              {nodes.map((n, i) => (
                <div key={n.id} className="flex gap-3">
                  <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-bg-primary border border-border flex items-center justify-center font-mono text-[10px] font-black">
                    {i + 1}
                  </div>
                  <div className="flex-1 bg-bg-primary border border-border rounded-xl p-3">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <span className="text-[10px] font-mono text-accent-amethyst">{n.type}</span>
                      <span className="text-[10px] text-secondary">·</span>
                      <span className="text-[10px] font-mono text-secondary truncate">{n.id}</span>
                    </div>
                    <p className="text-xs text-primary whitespace-pre-wrap leading-relaxed">{n.text || n.config?.content_text || n.config?.body || n.config?.question || n.label || 'Configure esta etapa no editor.'}</p>
                  </div>
                </div>
              ))}
            </>
          )}
        </div>
        <div className="p-4 border-t border-border flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 px-5 py-3 bg-bg-primary border border-border rounded-2xl text-sm font-bold"
          >
            Fechar
          </button>
          <button
            onClick={onUse}
            className="flex-1 px-5 py-3 bg-accent-amethyst hover:bg-accent-amethyst/90 text-white rounded-2xl text-sm font-black uppercase tracking-widest flex items-center justify-center gap-2"
          >
            <CheckCircle2 className="w-4 h-4" />
            Usar este kit
          </button>
        </div>
      </div>
    </div>
  );
}

function WhatsAppStep() {
  const [formData, setFormData] = useState({ phone_number_id: '', waba_id: '', access_token: '' });
  const [showToken, setShowToken] = useState(false);
  const [testResult, setTestResult] = useState<{ ok: boolean; message: string } | null>(null);
  const [savedBinding, setSavedBinding] = useState<WhatsAppStepResult | null>(null);

  const testMut = useMutation({
    mutationFn: () => integrationsApi.whatsapp.test({
      access_token: formData.access_token.trim(),
      phone_number_id: formData.phone_number_id.trim(),
    }),
    onSuccess: (res) => {
      if (res.ok) {
        setTestResult({
          ok: true,
          message: `OK — ${res.display_phone_number || ''} (${res.verified_name || 'sem nome'})`,
        });
      } else {
        const err = (res.error as { message?: string } | undefined)?.message || 'desconhecido';
        setTestResult({ ok: false, message: `Falhou: ${err}` });
      }
    },
    onError: (e) => toast.error((e as Error).message || 'Erro ao testar'),
  });

  const valid = formData.phone_number_id.length >= 6 &&
                formData.waba_id.length >= 6 &&
                formData.access_token.length > 20;

  const { data: bindingStatus } = useQuery({
    queryKey: ['onboarding-binding-status'],
    queryFn: integrationsApi.whatsapp.status,
    enabled: savedBinding !== null,
    refetchInterval: 5_000,
  });

  const saveMut = useMutation({
    mutationFn: () => onboardingApi.saveWhatsApp({
      access_token: formData.access_token.trim(),
      phone_number_id: formData.phone_number_id.trim(),
      waba_id: formData.waba_id.trim(),
    }),
    onSuccess: (res) => {
      if (res.binding) setSavedBinding(res.binding);
      setFormData(previous => ({ ...previous, access_token: '' }));
      track('onboarding_step_completed', { step: 'whatsapp', next: res.next_step });
    },
    onError: (e) => toast.error((e as Error).message || 'Erro ao conectar'),
  });

  const copy = (text: string, label = 'Copiado') => {
    navigator.clipboard.writeText(text);
    toast.success(label);
  };

  if (savedBinding) {
    return (
      <PostSaveSuccess
        binding={savedBinding}
        currentStatus={bindingStatus?.binding ?? null}
        onCopy={copy}
      />
    );
  }

  return (
    <div className="space-y-10">
      <div className="space-y-4">
        <h2 className="text-5xl font-black tracking-tighter leading-tight">Conecte sua conta <br/><span className="text-accent-amethyst">WhatsApp</span></h2>
        <p className="text-lg text-secondary font-medium">
          Cole as credenciais da Meta WhatsApp Cloud API. A gente valida na hora antes de salvar.
        </p>
      </div>

      <div className="bg-amber-500/10 border border-amber-500/20 p-6 rounded-3xl flex gap-4">
        <div className="w-10 h-10 rounded-2xl bg-amber-500/20 flex items-center justify-center flex-shrink-0">
          <ShieldCheck className="w-6 h-6 text-amber-500" />
        </div>
        <div className="text-xs text-amber-600/90 leading-relaxed font-medium space-y-1">
          <div>Use as credenciais do número que deseja conectar a esta conta.</div>
          <a
            href="https://developers.facebook.com/docs/whatsapp/cloud-api/get-started"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 underline font-bold"
          >
            Tutorial Meta Cloud API
            <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      </div>

      <div className="space-y-6 bg-bg-surface p-10 rounded-[40px] border border-border shadow-premium">
        <div className="grid grid-cols-2 gap-6">
          <div className="space-y-3">
            <label className="text-[10px] font-black uppercase tracking-[0.2em] text-secondary ml-1">Phone Number ID</label>
            <input
              type="text"
              value={formData.phone_number_id}
              onChange={e => setFormData({ ...formData, phone_number_id: e.target.value })}
              placeholder="Ex: 123456789012345"
              className="w-full bg-bg-primary border-2 border-border/50 rounded-2xl px-6 py-4 text-sm font-mono focus:border-accent-amethyst transition-all outline-none"
            />
          </div>
          <div className="space-y-3">
            <label className="text-[10px] font-black uppercase tracking-[0.2em] text-secondary ml-1">WABA ID</label>
            <input
              type="text"
              value={formData.waba_id}
              onChange={e => setFormData({ ...formData, waba_id: e.target.value })}
              placeholder="Ex: 987654321098765"
              className="w-full bg-bg-primary border-2 border-border/50 rounded-2xl px-6 py-4 text-sm font-mono focus:border-accent-amethyst transition-all outline-none"
            />
          </div>
        </div>

        <div className="space-y-3">
          <label className="text-[10px] font-black uppercase tracking-[0.2em] text-secondary ml-1">
            System User Access Token
          </label>
          <div className="relative">
            <textarea
              rows={3}
              value={formData.access_token}
              onChange={e => setFormData({ ...formData, access_token: e.target.value })}
              placeholder="EAAB..."
              className={`w-full bg-bg-primary border-2 border-border/50 rounded-2xl px-6 py-4 text-sm font-mono break-all focus:border-accent-amethyst transition-all outline-none resize-none pr-12 ${showToken ? '' : 'text-transparent caret-primary'}`}
              style={!showToken ? { WebkitTextSecurity: 'disc', textSecurity: 'disc' } as React.CSSProperties : undefined}
            />
            <button
              type="button"
              onClick={() => setShowToken(!showToken)}
              aria-label={showToken ? 'Ocultar token' : 'Mostrar token'}
              className="absolute right-4 top-4 text-secondary hover:text-primary"
            >
              {showToken ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
          <div className="text-[10px] text-secondary">
            System User permanente, com permissões whatsapp_business_messaging + whatsapp_business_management.
          </div>
        </div>

        <div className="flex items-center gap-3 pt-2">
          <button
            onClick={() => testMut.mutate()}
            disabled={!valid || testMut.isPending}
            className="px-5 py-3 bg-bg-primary border border-border hover:border-accent-amethyst/30 disabled:opacity-30 rounded-xl text-xs font-bold flex items-center gap-2"
          >
            <Shield className="w-3.5 h-3.5" />
            {testMut.isPending ? 'Testando…' : 'Testar credenciais'}
          </button>
          {testResult && (
            <span className={`text-xs flex items-center gap-1 font-bold ${testResult.ok ? 'text-emerald-400' : 'text-rose-400'}`}>
              {testResult.ok ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
              {testResult.message}
            </span>
          )}
        </div>

        <button
          onClick={() => saveMut.mutate()}
          disabled={!valid || saveMut.isPending}
          className="w-full py-5 bg-accent-amethyst text-white rounded-3xl text-sm font-black uppercase tracking-[0.2em] shadow-2xl shadow-accent-amethyst/40 hover:scale-[1.02] active:scale-95 disabled:opacity-30 disabled:scale-100 transition-all flex items-center justify-center gap-3"
        >
          {saveMut.isPending ? 'Conectando…' : 'Conectar WhatsApp'}
          <ArrowRight className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
}


function PostSaveSuccess({
  binding, currentStatus, onCopy,
}: {
  binding: WhatsAppStepResult;
  currentStatus: import('../api/integrations').WaBinding | null;
  onCopy: (t: string, l?: string) => void;
}) {
  const navigate = useNavigate();
  const inboundReceived = (currentStatus?.inbound_count ?? 0) > 0;

  return (
    <div className="space-y-8">
      <div className="space-y-4">
        <h2 className="text-5xl font-black tracking-tighter leading-tight">
          Quase lá. <br/>
          <span className="text-accent-amethyst">Configure o webhook na Meta.</span>
        </h2>
        <p className="text-lg text-secondary font-medium">
          Cole estes 2 valores no painel do app no developers.facebook.com → WhatsApp → Configuração:
        </p>
      </div>

      <div className="grid gap-3">
        <CopyRow
          label="Webhook callback URL"
          value={binding.webhook_url}
          onCopy={() => onCopy(binding.webhook_url, 'URL copiada')}
        />
        <CopyRow
          label="Verify Token"
          value={binding.verify_token}
          onCopy={() => onCopy(binding.verify_token, 'Token copiado')}
        />
      </div>

      <div className="bg-bg-surface border border-border rounded-3xl p-6 space-y-3">
        <h3 className="text-[10px] font-black uppercase tracking-widest text-secondary">
          Passos no painel da Meta
        </h3>
        <ol className="text-xs text-primary space-y-1.5 list-decimal list-inside leading-relaxed">
          <li>Abra <a href="https://developers.facebook.com" target="_blank" rel="noreferrer" className="text-accent-amethyst underline">developers.facebook.com</a> → seu app → WhatsApp → Configuração.</li>
          <li>Clique em <strong>Editar</strong> ao lado de "Webhook" e cole a URL e o Verify Token acima.</li>
          <li>Em <strong>Webhook fields</strong>, assine ao menos: <code className="bg-bg-primary px-1 rounded">messages</code>.</li>
          <li>Mande uma mensagem de qualquer celular para o número conectado pra confirmar.</li>
        </ol>
      </div>

      <div
        className={`rounded-2xl p-5 border ${
          inboundReceived
            ? 'bg-emerald-500/5 border-emerald-500/30'
            : 'bg-amber-500/5 border-amber-500/30'
        }`}
      >
        <div className="flex items-center gap-2 mb-2">
          {inboundReceived ? (
            <Inbox className="w-5 h-5 text-emerald-400" />
          ) : (
            <Zap className="w-5 h-5 text-amber-300 animate-pulse" />
          )}
          <span className={`text-[10px] font-black uppercase tracking-widest ${inboundReceived ? 'text-emerald-400' : 'text-amber-300'}`}>
            {inboundReceived ? 'Tudo conectado — primeira mensagem chegou' : 'Aguardando primeira mensagem'}
          </span>
        </div>
        <p className="text-xs text-secondary leading-relaxed">
          {inboundReceived
            ? `Total recebido: ${currentStatus?.inbound_count}. Abra seus funis, teste as etapas e publique quando estiver pronto.`
            : 'Confirme o webhook na Meta acima — assim que chegar a primeira msg, você verá aqui em tempo real.'}
        </p>
        {!inboundReceived && binding.subscribe_error && (
          <div className="mt-3 text-[11px] text-amber-300 flex items-start gap-1">
            <AlertTriangle className="w-3 h-3 mt-0.5 flex-shrink-0" />
            <span>Auto-subscribe falhou: {binding.subscribe_error}. Revise a conexão na página Integrações.</span>
          </div>
        )}
      </div>

      <div className="flex gap-3">
        <button
          onClick={() => navigate('/dashboard')}
          className="flex-1 py-4 bg-bg-primary border-2 border-border hover:border-accent-amethyst/30 rounded-2xl text-xs font-black uppercase tracking-widest"
        >
          Ver próximos passos
        </button>
        <button
          onClick={() => navigate(inboundReceived ? '/blueprints' : '/integrations')}
          className="flex-1 py-4 bg-accent-amethyst text-white rounded-2xl text-xs font-black uppercase tracking-widest flex items-center justify-center gap-2"
        >
          <CheckCircle2 className="w-4 h-4" />
          {inboundReceived ? 'Preparar meu funil' : 'Ver detalhes em Integrações'}
        </button>
      </div>
    </div>
  );
}


function CopyRow({
  label, value, onCopy,
}: {
  label: string;
  value: string;
  onCopy: () => void;
}) {
  return (
    <div className="bg-bg-primary border border-border rounded-2xl p-4">
      <div className="text-[10px] font-black uppercase tracking-widest text-secondary mb-1.5">
        {label}
      </div>
      <div className="flex items-center justify-between gap-3">
        <code className="font-mono text-xs break-all flex-1">{value}</code>
        <button
          onClick={onCopy}
          className="px-3 py-1.5 bg-bg-surface border border-border hover:border-accent-amethyst/30 rounded-lg text-[11px] font-bold flex items-center gap-1.5 flex-shrink-0"
        >
          <Copy className="w-3 h-3" />
          Copiar
        </button>
      </div>
    </div>
  );
}
