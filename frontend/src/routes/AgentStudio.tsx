import { useEffect, useMemo, useState, useRef } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Bot,
  Camera,
  CheckCircle2,
  FileText,
  HelpCircle,
  Library,
  Plus,
  Rocket,
  Sparkles,
  Trash2,
  Send,
  Sliders,
  Clock,
  Cpu,
  MessageSquare,
  Play,
  RotateCcw,
  Check,
  User,
  ShieldAlert,
} from 'lucide-react';
import { agentsApi, type AgentDraft, type AgentSummary } from '../api/agents';
import { toast } from '../lib/toast';

type Tab = 'personalidade' | 'instrucoes' | 'base' | 'exemplos' | 'versoes';

const TABS: { id: Tab; label: string; Icon: typeof Sparkles }[] = [
  { id: 'personalidade', label: 'Identidade & Modelo', Icon: Sparkles },
  { id: 'instrucoes', label: 'Instruções & Regras', Icon: FileText },
  { id: 'base', label: 'Base de Conhecimento', Icon: Library },
  { id: 'exemplos', label: 'FAQ & Exemplos', Icon: HelpCircle },
  { id: 'versoes', label: 'Versões & WhatsApp', Icon: Rocket },
];

const AI_MODELS = [
  { id: 'gemini-2.5-flash', name: 'Gemini 2.5 Flash', provider: 'Google', badge: 'Recomendado', speed: 'Ultrarrápido (500ms)' },
  { id: 'gpt-4o-mini', name: 'GPT-4o Mini', provider: 'OpenAI', badge: 'Alta Precisão', speed: 'Rápido (900ms)' },
  { id: 'claude-3-5-haiku', name: 'Claude 3.5 Haiku', provider: 'Anthropic', badge: 'Raciocínio Fluido', speed: 'Rápido (800ms)' },
  { id: 'llama-3.3-70b', name: 'Llama 3.3 70B', provider: 'Groq', badge: 'Open Source', speed: 'Instantâneo (350ms)' },
];

export default function AgentStudio() {
  const qc = useQueryClient();
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const { data: agents = [], isLoading } = useQuery({
    queryKey: ['studio-agents'],
    queryFn: agentsApi.list,
  });

  const { data: pubStatus } = useQuery({
    queryKey: ['studio-publish-status'],
    queryFn: agentsApi.publishStatus,
  });

  // Auto-seleciona o primeiro agente
  useEffect(() => {
    if (selectedId == null && agents.length > 0) setSelectedId(agents[0].id);
  }, [agents, selectedId]);

  const createMutation = useMutation({
    mutationFn: agentsApi.create,
    onSuccess: (res) => {
      toast.success('Novo agente de IA criado com sucesso.');
      qc.invalidateQueries({ queryKey: ['studio-agents'] });
      setSelectedId(res.agent.id);
    },
    onError: (e) => toast.error((e as Error).message),
  });

  const removeMutation = useMutation({
    mutationFn: agentsApi.remove,
    onSuccess: () => {
      toast.success('Agente removido.');
      qc.invalidateQueries({ queryKey: ['studio-agents'] });
      setSelectedId(null);
    },
    onError: (e) => toast.error((e as Error).message),
  });

  const handleNew = () => {
    const name = window.prompt('Qual o nome do atendente de IA? (Ex: Bia - Vendas, Carlos - Suporte)');
    if (name && name.trim()) createMutation.mutate({ name: name.trim() });
  };

  const selectedAgent = agents.find((a) => a.id === selectedId) ?? null;
  const publishedVersionId = pubStatus?.published?.version_id ?? null;

  return (
    <div className="flex h-full w-full bg-zinc-950 text-zinc-100 overflow-hidden font-sans">
      {/* ═══ COLUNA LATERAL ESQUERDA: LISTA DE AGENTES ═══ */}
      <aside className="w-80 flex-shrink-0 border-r border-zinc-800/80 bg-zinc-900/50 flex flex-col">
        {/* Header da Sidebar */}
        <div className="px-5 py-4 border-b border-zinc-800/80 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center">
              <Bot className="w-4 h-4 text-indigo-400" />
            </div>
            <span className="text-xs font-black uppercase tracking-wider text-zinc-300">
              Atendentes de IA
            </span>
          </div>
          <button
            onClick={handleNew}
            disabled={createMutation.isPending}
            className="text-xs font-bold px-3 py-1.5 rounded-lg bg-indigo-600 text-white hover:bg-indigo-500 flex items-center gap-1.5 shadow-sm shadow-indigo-600/20 transition-all active:scale-95"
          >
            <Plus className="w-3.5 h-3.5" />
            Novo
          </button>
        </div>

        {/* Lista */}
        <div className="flex-1 overflow-y-auto p-3 space-y-1.5">
          {isLoading && (
            <div className="p-6 text-center text-xs text-zinc-500 animate-pulse">
              Carregando agentes de IA…
            </div>
          )}

          {!isLoading && agents.length === 0 && (
            <div className="p-8 text-center space-y-3">
              <div className="w-12 h-12 rounded-2xl bg-zinc-800/60 border border-zinc-700/50 flex items-center justify-center mx-auto text-zinc-500">
                <Bot className="w-6 h-6" />
              </div>
              <p className="text-xs text-zinc-400 font-medium leading-relaxed">
                Nenhum agente cadastrado ainda. Clique em <strong>Novo</strong> para criar seu primeiro atendente.
              </p>
            </div>
          )}

          {agents.map((a) => {
            const isSelected = selectedId === a.id;
            const isLive = a.published_version_id != null;
            return (
              <button
                key={a.id}
                onClick={() => setSelectedId(a.id)}
                className={`w-full text-left p-3 rounded-xl flex items-center gap-3 transition-all border ${
                  isSelected
                    ? 'bg-zinc-800/80 border-indigo-500/40 shadow-sm shadow-black/40'
                    : 'bg-zinc-900/30 border-transparent hover:bg-zinc-800/40 hover:border-zinc-800'
                }`}
              >
                <div
                  className="w-10 h-10 rounded-xl flex items-center justify-center text-sm font-black text-white flex-shrink-0 shadow-md"
                  style={{ backgroundColor: a.avatar || '#6366f1' }}
                >
                  {a.name?.charAt(0).toUpperCase() || 'A'}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-bold text-zinc-100 truncate">{a.name}</span>
                    {isLive && (
                      <span className="flex items-center gap-1 text-[10px] font-black uppercase tracking-wider text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded-md border border-emerald-500/20">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                        Zap
                      </span>
                    )}
                  </div>
                  <div className="text-[11px] text-zinc-400 font-medium mt-0.5 flex items-center gap-2">
                    <span>Draft v{a.draft_version || 1}</span>
                    <span className="text-zinc-600">•</span>
                    <span>ID #{a.id}</span>
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </aside>

      {/* ═══ COLUNA CENTRAL E DIREITA: EDITOR & SIMULADOR ═══ */}
      <main className="flex-1 min-w-0 overflow-y-auto bg-zinc-950">
        {selectedAgent ? (
          <AgentEditor
            key={selectedAgent.id}
            agent={selectedAgent}
            publishedVersionId={publishedVersionId}
            onDelete={() => {
              if (confirm(`Tem certeza que deseja apagar o agente "${selectedAgent.name}"?`)) {
                removeMutation.mutate(selectedAgent.id);
              }
            }}
          />
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-center p-12 space-y-4">
            <div className="w-16 h-16 rounded-3xl bg-zinc-900 border border-zinc-800 flex items-center justify-center shadow-xl">
              <Bot className="w-8 h-8 text-zinc-500" />
            </div>
            <h3 className="text-lg font-bold text-zinc-200">Estúdio de Inteligência Artificial</h3>
            <p className="text-sm text-zinc-400 max-w-sm">
              Selecione um atendente à esquerda ou crie um novo para configurar a inteligência do seu WhatsApp oficial.
            </p>
          </div>
        )}
      </main>
    </div>
  );
}

// ── EDITOR COMPLETO DE AGENTE ────────────────────────────────────────

function AgentEditor({
  agent,
  publishedVersionId,
  onDelete,
}: {
  agent: AgentSummary;
  publishedVersionId: number | null;
  onDelete: () => void;
}) {
  const qc = useQueryClient();
  const [tab, setTab] = useState<Tab>('personalidade');
  const [draft, setDraft] = useState<AgentDraft>(agent.draft ?? {});
  const [name, setName] = useState(agent.name);
  const [dirty, setDirty] = useState(false);
  const [showSimulator, setShowSimulator] = useState(false);

  // Sincroniza estado quando muda o agente ativo
  useEffect(() => {
    setDraft(agent.draft ?? {});
    setName(agent.name);
    setDirty(false);
  }, [agent.id]);

  const saveMutation = useMutation({
    mutationFn: () => agentsApi.update(agent.id, { name, draft }),
    onSuccess: () => {
      setDirty(false);
      toast.success('Configurações salvas.');
      qc.invalidateQueries({ queryKey: ['studio-agents'] });
    },
    onError: (e) => toast.error((e as Error).message),
  });

  const snapshotMutation = useMutation({
    mutationFn: (note: string) => agentsApi.snapshot(agent.id, note),
    onSuccess: () => {
      toast.success('Versão congelada criada.');
      qc.invalidateQueries({ queryKey: ['studio-agents'] });
    },
    onError: (e) => toast.error((e as Error).message),
  });

  const publishMutation = useMutation({
    mutationFn: (versionId: number) => agentsApi.publish(agent.id, versionId),
    onSuccess: (res) => {
      toast.success(`Versão #${res.published_version_id} ativada para o WhatsApp!`);
      qc.invalidateQueries({ queryKey: ['studio-publish-status'] });
      qc.invalidateQueries({ queryKey: ['studio-agents'] });
    },
    onError: (e) => toast.error((e as Error).message),
  });

  const versions = useMemo(
    () => [...(agent.versions ?? [])].sort((a, b) => b.version_number - a.version_number),
    [agent.versions],
  );

  const update = (patch: Partial<AgentDraft>) => {
    setDraft((d) => ({ ...d, ...patch }));
    setDirty(true);
  };

  const selectedModelId = (draft.model as string) || 'gemini-2.5-flash';
  const selectedModel = AI_MODELS.find((m) => m.id === selectedModelId) || AI_MODELS[0];

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-6">
      {/* ═══ TOPO: IDENTIFICAÇÃO E AÇÕES PRINCIPAIS ═══ */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-zinc-900/70 p-6 rounded-2xl border border-zinc-800 shadow-xl">
        <div className="flex items-center gap-4 min-w-0">
          <div
            className="w-14 h-14 rounded-2xl flex items-center justify-center text-2xl font-black text-white flex-shrink-0 shadow-lg"
            style={{ backgroundColor: agent.avatar || '#6366f1' }}
          >
            {(name || agent.name).charAt(0).toUpperCase() || 'A'}
          </div>
          <div className="flex-1 min-w-0">
            <input
              type="text"
              value={name}
              onChange={(e) => {
                setName(e.target.value);
                setDirty(true);
              }}
              className="w-full text-xl font-black bg-transparent text-zinc-100 outline-none border-b border-transparent focus:border-indigo-500 transition-all px-0 pb-0.5 placeholder:text-zinc-600"
              placeholder="Nome do agente..."
            />
            <div className="flex items-center gap-3 mt-1 text-xs">
              <span className="font-bold text-zinc-400">Rascunho v{agent.draft_version || 1}</span>
              <span className="text-zinc-600">•</span>
              <span className="text-zinc-400 flex items-center gap-1.5">
                <Cpu className="w-3.5 h-3.5 text-indigo-400" />
                {selectedModel.name}
              </span>
              {dirty && (
                <span className="flex items-center gap-1 font-bold text-amber-400 animate-pulse text-[11px]">
                  ● Alterações não salvas
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Botões de Ação */}
        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={() => setShowSimulator(!showSimulator)}
            className={`px-3.5 py-2 rounded-xl text-xs font-bold border transition-all flex items-center gap-2 ${
              showSimulator
                ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                : 'bg-zinc-800 hover:bg-zinc-700 border-zinc-700 text-zinc-200'
            }`}
          >
            <MessageSquare className="w-4 h-4 text-emerald-400" />
            {showSimulator ? 'Fechar Teste' : 'Testar no Zap'}
          </button>

          <button
            onClick={() => saveMutation.mutate()}
            disabled={!dirty || saveMutation.isPending}
            className="px-4 py-2 rounded-xl bg-indigo-600 text-white text-xs font-bold shadow-sm shadow-indigo-600/30 hover:bg-indigo-500 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {saveMutation.isPending ? 'Salvando…' : 'Salvar Alterações'}
          </button>

          <button
            onClick={() => {
              const note = window.prompt('Descrição desta versão congelada (Ex: Prompt ajustado para fechar vendas):') ?? '';
              snapshotMutation.mutate(note);
            }}
            disabled={snapshotMutation.isPending}
            className="px-3.5 py-2 rounded-xl border border-zinc-700 bg-zinc-800/80 hover:bg-zinc-700 text-xs font-bold text-zinc-200 flex items-center gap-1.5 transition-all"
            title="Congelar rascunho em uma versão fixa"
          >
            <Camera className="w-3.5 h-3.5 text-zinc-400" />
            Congelar Versão
          </button>

          <button
            onClick={onDelete}
            className="p-2 rounded-xl border border-zinc-800 bg-zinc-900/80 hover:border-red-500/50 hover:bg-red-500/10 text-zinc-400 hover:text-red-400 transition-all"
            title="Excluir agente"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* ═══ SIMULADOR DO WHATSAPP (SE ATIVO) ═══ */}
      {showSimulator && (
        <WhatsAppSimulator
          agentName={name}
          instructions={draft.instrucoes as string || ''}
          knowledge={draft.base_conhecimento as string || ''}
          faqs={(draft.faqs as { q: string; a: string }[]) || []}
          onClose={() => setShowSimulator(false)}
        />
      )}

      {/* ═══ ABAS ESTILO SHADCN / LINEAR ═══ */}
      <div className="flex gap-1.5 p-1 bg-zinc-900/90 rounded-xl border border-zinc-800 shadow-sm overflow-x-auto">
        {TABS.map((t) => {
          const isActive = tab === t.id;
          return (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`flex-1 min-w-[130px] flex items-center justify-center gap-2 px-4 py-2.5 text-xs font-bold rounded-lg transition-all ${
                isActive
                  ? 'bg-zinc-800 text-white shadow-sm border border-zinc-700/80'
                  : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50'
              }`}
            >
              <t.Icon className={`w-4 h-4 ${isActive ? 'text-indigo-400' : 'text-zinc-500'}`} />
              {t.label}
            </button>
          );
        })}
      </div>

      {/* ═══ CONTEÚDO DAS ABAS ═══ */}
      <div className="bg-zinc-900/50 border border-zinc-800 rounded-2xl p-6 shadow-xl space-y-6">
        {/* ABA 1: IDENTIDADE & MODELO */}
        {tab === 'personalidade' && (
          <div className="space-y-6">
            {/* Seletor de Modelo de IA */}
            <div>
              <label className="text-xs font-bold uppercase tracking-wider text-zinc-400 block mb-2">
                Motor de Inteligência Artificial
              </label>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {AI_MODELS.map((m) => {
                  const isSelected = selectedModelId === m.id;
                  return (
                    <button
                      key={m.id}
                      type="button"
                      onClick={() => update({ model: m.id })}
                      className={`text-left p-3.5 rounded-xl border transition-all flex items-start justify-between ${
                        isSelected
                          ? 'bg-indigo-500/10 border-indigo-500/50 shadow-sm ring-1 ring-indigo-500/30'
                          : 'bg-zinc-900/80 border-zinc-800 hover:border-zinc-700'
                      }`}
                    >
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-bold text-zinc-100">{m.name}</span>
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-zinc-800 text-zinc-300">
                            {m.badge}
                          </span>
                        </div>
                        <div className="text-xs text-zinc-400 mt-1 flex items-center gap-2">
                          <span>{m.provider}</span>
                          <span className="text-zinc-600">•</span>
                          <span className="text-emerald-400 font-medium">{m.speed}</span>
                        </div>
                      </div>
                      {isSelected && <Check className="w-4 h-4 text-indigo-400 mt-1" />}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Configurações de Comportamento */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2 border-t border-zinc-800/80">
              {/* Slider de Temperatura / Criatividade */}
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold text-zinc-300">Criatividade (Temperatura)</span>
                  <span className="font-mono text-indigo-400 font-bold">
                    {((draft.temperature as number) ?? 0.3).toFixed(1)}
                  </span>
                </div>
                <input
                  type="range"
                  min="0.0"
                  max="1.0"
                  step="0.1"
                  value={(draft.temperature as number) ?? 0.3}
                  onChange={(e) => update({ temperature: parseFloat(e.target.value) })}
                  className="w-full accent-indigo-500 cursor-pointer"
                />
                <div className="flex justify-between text-[10px] text-zinc-500">
                  <span>0.0 (Ultra Preciso & Fiel)</span>
                  <span>1.0 (Mais Criativo)</span>
                </div>
              </div>

              {/* Delay Humanizado de Resposta no WhatsApp */}
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold text-zinc-300">Delay "Digitando..." no WhatsApp</span>
                  <span className="font-mono text-emerald-400 font-bold">
                    {((draft.delay_seconds as number) ?? 3)}s
                  </span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="10"
                  step="1"
                  value={(draft.delay_seconds as number) ?? 3}
                  onChange={(e) => update({ delay_seconds: parseInt(e.target.value) })}
                  className="w-full accent-emerald-500 cursor-pointer"
                />
                <div className="flex justify-between text-[10px] text-zinc-500">
                  <span>1s (Quase instantâneo)</span>
                  <span>10s (Simula digitação longa)</span>
                </div>
              </div>
            </div>

            {/* Tom de Voz e Personalidade */}
            <div className="space-y-2 pt-2 border-t border-zinc-800/80">
              <label className="text-xs font-bold uppercase tracking-wider text-zinc-400 block">
                Tom de Voz e Estilo de Comunicação
              </label>
              <textarea
                value={(draft.personalidade as string) ?? ''}
                onChange={(e) => update({ personalidade: e.target.value })}
                rows={5}
                className="w-full bg-zinc-950 border border-zinc-800 rounded-xl p-4 text-sm text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all resize-none leading-relaxed"
                placeholder="Ex: Fale de forma amigável, direta e profissional. Use emojis com moderação (máximo 1 ou 2 por mensagem). Trate o cliente pelo primeiro nome sempre que possível. Nunca use termos excessivamente técnicos..."
              />
            </div>
          </div>
        )}

        {/* ABA 2: INSTRUÇÕES & REGRAS (SYSTEM PROMPT) */}
        {tab === 'instrucoes' && (
          <div className="space-y-4">
            <div>
              <h4 className="text-sm font-bold text-zinc-200 mb-1">Prompt do Sistema (System Instructions)</h4>
              <p className="text-xs text-zinc-400">
                Estas são as regras invioláveis que o modelo seguirá em todas as interações no WhatsApp.
              </p>
            </div>
            <textarea
              value={(draft.instrucoes as string) ?? ''}
              onChange={(e) => update({ instrucoes: e.target.value })}
              rows={12}
              className="w-full bg-zinc-950 border border-zinc-800 rounded-xl p-4 font-mono text-xs text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all resize-none leading-relaxed"
              placeholder={`# OBJETIVO PRINCIPAL
Você é o atendente de vendas da [Nome da Empresa]. Seu foco é tirar dúvidas do cliente, entender a necessidade dele e direcioná-lo para fechar a compra ou agendar uma reunião.

# REGRAS DE ATENDIMENTO
1. Seja objetivo e não envie mensagens excessivamente longas (limite a 2 ou 3 parágrafos curtos).
2. Faça perguntas abertas para qualificar o interesse do lead.
3. Se o cliente perguntar de preços, apresente as opções e ofereça o link de compra direto.

# LIMITES E TRANSBORDO HUMANO
- Se o cliente pedir expressamente para falar com um humano, responda cordialmente: "Com certeza! Estou transferindo seu atendimento para a nossa equipe agora mesmo" e pause o fluxo.`}
            />
          </div>
        )}

        {/* ABA 3: BASE DE CONHECIMENTO */}
        {tab === 'base' && (
          <div className="space-y-4">
            <div>
              <h4 className="text-sm font-bold text-zinc-200 mb-1">Base de Conhecimento e Catálogo</h4>
              <p className="text-xs text-zinc-400">
                Cole aqui todas as informações da sua empresa, produtos, serviços, preços, formas de pagamento e links de checkout. A IA usará apenas essas informações para responder fatos aos clientes.
              </p>
            </div>
            <textarea
              value={(draft.base_conhecimento as string) ?? ''}
              onChange={(e) => update({ base_conhecimento: e.target.value })}
              rows={12}
              className="w-full bg-zinc-950 border border-zinc-800 rounded-xl p-4 text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all resize-none leading-relaxed"
              placeholder={`PLANOS E PREÇOS:
- Plano Essencial: R$ 97/mês (Até 1.000 leads, 1 número de WhatsApp)
- Plano Profissional: R$ 149/mês (Leads ilimitados, IA autônoma e disparos em massa)
- Link de Checkout do Plano Profissional: https://seusite.com/checkout/pro

FORMAS DE PAGAMENTO:
- Cartão de crédito em até 12x ou Pix à vista com 5% de desconto.

POLÍTICA DE CANCELAMENTO:
- Garantia incondicional de 7 dias com reembolso integral.`}
            />
          </div>
        )}

        {/* ABA 4: FAQ & EXEMPLOS (FEW-SHOT EXAMPLES) */}
        {tab === 'exemplos' && (
          <div className="space-y-6">
            <FaqAndFewShotEditor
              faqs={(draft.faqs as { q: string; a: string }[]) ?? []}
              onChange={(faqs) => update({ faqs })}
            />
          </div>
        )}

        {/* ABA 5: VERSÕES & PUBLICAÇÃO PARA O WHATSAPP */}
        {tab === 'versoes' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="text-sm font-bold text-zinc-200">Histórico de Versões do Agente</h4>
                <p className="text-xs text-zinc-400">
                  Cada snapshot é uma cópia segura e imutável. Você pode ativar qualquer versão anterior a qualquer momento.
                </p>
              </div>
              <button
                onClick={() => {
                  const note = window.prompt('Descrição para esta nova versão (Ex: Atualização de preços):') ?? '';
                  snapshotMutation.mutate(note);
                }}
                disabled={snapshotMutation.isPending}
                className="px-4 py-2 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-xs font-bold text-zinc-100 flex items-center gap-1.5 border border-zinc-700 transition-all"
              >
                <Plus className="w-4 h-4" />
                Criar Nova Versão
              </button>
            </div>

            {versions.length === 0 ? (
              <div className="text-center py-12 border border-dashed border-zinc-800 rounded-2xl p-6">
                <p className="text-xs text-zinc-500">
                  Nenhuma versão congelada ainda. Clique no botão acima ou em <strong>Congelar Versão</strong> no topo para criar sua v1.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {versions.map((v) => {
                  const isActive = v.id === publishedVersionId;
                  return (
                    <div
                      key={v.id}
                      className={`p-4 rounded-xl border flex items-center justify-between transition-all ${
                        isActive
                          ? 'bg-emerald-500/5 border-emerald-500/30 ring-1 ring-emerald-500/20 shadow-lg shadow-emerald-500/5'
                          : 'bg-zinc-900/60 border-zinc-800 hover:border-zinc-700'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-zinc-800 border border-zinc-700 flex items-center justify-center font-mono font-bold text-xs text-zinc-200">
                          v{v.version_number}
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-bold text-zinc-100">
                              {v.note || `Versão #${v.version_number}`}
                            </span>
                            {isActive && (
                              <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-[10px] font-black uppercase tracking-wider flex items-center gap-1">
                                <CheckCircle2 className="w-3 h-3" />
                                Ativa no WhatsApp
                              </span>
                            )}
                          </div>
                          <div className="text-[11px] text-zinc-500 mt-0.5">
                            {v.created_at ? new Date(v.created_at).toLocaleString('pt-BR') : ''}
                          </div>
                        </div>
                      </div>

                      {!isActive && (
                        <button
                          onClick={() => {
                            if (confirm(`Ativar v${v.version_number} para responder ao vivo no WhatsApp oficial?`)) {
                              publishMutation.mutate(v.id);
                            }
                          }}
                          disabled={publishMutation.isPending}
                          className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold transition-all shadow-sm shadow-emerald-600/20 active:scale-95"
                        >
                          Publicar no WhatsApp
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ── EDITOR DE FAQ & FEW-SHOT EXAMPLES ─────────────────────────────────

function FaqAndFewShotEditor({
  faqs,
  onChange,
}: {
  faqs: { q: string; a: string }[];
  onChange: (faqs: { q: string; a: string }[]) => void;
}) {
  const update = (i: number, patch: Partial<{ q: string; a: string }>) => {
    onChange(faqs.map((f, idx) => (idx === i ? { ...f, ...patch } : f)));
  };
  const remove = (i: number) => onChange(faqs.filter((_, idx) => idx !== i));
  const add = () => onChange([...faqs, { q: '', a: '' }]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h4 className="text-sm font-bold text-zinc-200">Exemplos de Diálogo & Perguntas Frequentes (FAQ)</h4>
          <p className="text-xs text-zinc-400">
            Cadastre pares exatos de como o cliente pergunta e como a IA deve responder.
          </p>
        </div>
        <button
          onClick={add}
          className="px-3 py-1.5 rounded-lg bg-indigo-600/20 text-indigo-400 hover:bg-indigo-600/30 border border-indigo-500/30 text-xs font-bold flex items-center gap-1.5 transition-all"
        >
          <Plus className="w-3.5 h-3.5" />
          Adicionar Exemplo
        </button>
      </div>

      {faqs.length === 0 && (
        <div className="text-center py-8 border border-dashed border-zinc-800 rounded-xl p-6">
          <p className="text-xs text-zinc-500">
            Nenhum exemplo adicionado. Clique no botão acima para ensinar respostas específicas para perguntas frequentes.
          </p>
        </div>
      )}

      {faqs.map((f, i) => (
        <div
          key={i}
          className="bg-zinc-950 border border-zinc-800 rounded-xl p-4 space-y-3 shadow-inner"
        >
          <div className="flex items-center justify-between">
            <span className="text-[10px] uppercase font-black tracking-wider text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20">
              Exemplo #{i + 1}
            </span>
            <button
              onClick={() => remove(i)}
              className="p-1.5 rounded-lg text-zinc-500 hover:text-red-400 hover:bg-red-500/10 transition-all"
              title="Excluir exemplo"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
          <div className="space-y-2">
            <div>
              <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider block mb-1">
                Pergunta do Cliente (Lead)
              </span>
              <input
                type="text"
                value={f.q}
                onChange={(e) => update(i, { q: e.target.value })}
                placeholder="Ex: Vocês aceitam pagamento via Pix parcelado?"
                className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-3.5 py-2 text-xs font-medium text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-indigo-500 transition-all"
              />
            </div>
            <div>
              <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider block mb-1">
                Resposta Ideal do Atendente de IA
              </span>
              <textarea
                value={f.a}
                onChange={(e) => update(i, { a: e.target.value })}
                placeholder="Ex: Aceitamos Pix à vista com 5% de desconto imediato! Para parcelamento, você pode pagar em até 12x no cartão de crédito."
                rows={2}
                className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-3.5 py-2 text-xs text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:border-indigo-500 transition-all resize-none leading-relaxed"
              />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

// ── SIMULADOR DE CHAT DO WHATSAPP (PLAYGROUND) ─────────────────────────

function WhatsAppSimulator({
  agentName,
  instructions,
  knowledge,
  faqs,
  onClose,
}: {
  agentName: string;
  instructions: string;
  knowledge: string;
  faqs: { q: string; a: string }[];
  onClose: () => void;
}) {
  const [messages, setMessages] = useState<{ sender: 'user' | 'bot'; text: string; time: string }[]>([
    {
      sender: 'bot',
      text: `Olá! Sou ${agentName || 'o assistente virtual'}. Como posso te ajudar hoje?`,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  const handleSend = () => {
    if (!input.trim() || isTyping) return;
    const userMsg = input.trim();
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    setMessages((prev) => [...prev, { sender: 'user', text: userMsg, time }]);
    setInput('');
    setIsTyping(true);

    // Simulação inteligente baseada em FAQs locais ou prompt
    setTimeout(() => {
      let botResponse = '';
      const matchedFaq = faqs.find((f) =>
        f.q && userMsg.toLowerCase().includes(f.q.toLowerCase().slice(0, 15))
      );

      if (matchedFaq && matchedFaq.a) {
        botResponse = matchedFaq.a;
      } else if (knowledge && knowledge.toLowerCase().includes(userMsg.toLowerCase().slice(0, 10))) {
        botResponse = `Com base nas nossas informações: temos exatamente o que você procura! Quer que eu te envie o link direto para contratação?`;
      } else {
        botResponse = `Entendido! Estou processando seu pedido de acordo com as diretrizes da empresa. Posso tirar mais alguma dúvida específica?`;
      }

      setMessages((prev) => [
        ...prev,
        {
          sender: 'bot',
          text: botResponse,
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
      setIsTyping(false);
    }, 1200);
  };

  return (
    <div className="bg-[#0b141a] border border-zinc-800 rounded-2xl overflow-hidden shadow-2xl transition-all animate-in fade-in duration-200">
      {/* WhatsApp Header */}
      <div className="bg-[#202c33] px-4 py-3 flex items-center justify-between border-b border-zinc-800">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-full bg-emerald-600 flex items-center justify-center text-sm font-black text-white">
            {agentName.charAt(0).toUpperCase() || 'A'}
          </div>
          <div>
            <div className="text-sm font-bold text-zinc-100">{agentName} (Simulação)</div>
            <div className="text-[10px] text-emerald-400 flex items-center gap-1 font-medium">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              online
            </div>
          </div>
        </div>
        <button
          onClick={onClose}
          className="text-xs text-zinc-400 hover:text-zinc-100 px-2 py-1 rounded bg-zinc-800 hover:bg-zinc-700 transition-all font-bold"
        >
          Fechar
        </button>
      </div>

      {/* WhatsApp Chat Area */}
      <div className="h-72 p-4 overflow-y-auto space-y-3 bg-[radial-gradient(#111b21_1px,transparent_1px)] [background-size:16px_16px]">
        {messages.map((m, i) => (
          <div
            key={i}
            className={`flex flex-col ${m.sender === 'user' ? 'items-end' : 'items-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-xs shadow-md ${
                m.sender === 'user'
                  ? 'bg-[#005c4b] text-zinc-100 rounded-br-none'
                  : 'bg-[#202c33] text-zinc-100 rounded-bl-none'
              }`}
            >
              <p className="leading-relaxed">{m.text}</p>
              <span className="text-[9px] text-zinc-400 float-right mt-1 ml-2 font-mono">
                {m.time}
              </span>
            </div>
          </div>
        ))}

        {isTyping && (
          <div className="flex items-center gap-1 bg-[#202c33] text-zinc-400 text-xs px-3 py-2 rounded-xl w-fit">
            <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-bounce" />
            <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-bounce [animation-delay:0.2s]" />
            <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-bounce [animation-delay:0.4s]" />
            <span className="text-[11px] font-medium ml-1">digitando...</span>
          </div>
        )}
        <div ref={endRef} />
      </div>

      {/* WhatsApp Input Footer */}
      <div className="bg-[#202c33] p-3 flex items-center gap-2 border-t border-zinc-800">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder="Envie uma mensagem para testar o bot..."
          className="flex-1 bg-[#2a3942] border border-transparent focus:border-emerald-500 rounded-xl px-4 py-2 text-xs text-zinc-100 placeholder:text-zinc-400 focus:outline-none transition-all"
        />
        <button
          onClick={handleSend}
          disabled={!input.trim() || isTyping}
          className="w-9 h-9 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-white flex items-center justify-center transition-all shadow-md active:scale-95"
        >
          <Send className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
