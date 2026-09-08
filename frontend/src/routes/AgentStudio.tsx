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
  X,
  AlertTriangle,
  ArrowRight,
  Wand2,
  Zap,
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

const AVATAR_COLORS = ['#7c3aed', '#2563eb', '#059669', '#d97706', '#e11d48', '#4f46e5', '#0891b2'];

interface AgentPreset {
  id: string;
  name: string;
  role: string;
  badge: string;
  avatar: string;
  icon: string;
  description: string;
  highlights: string[];
  modelId: string;
  draft: AgentDraft;
}

const AGENT_PRESETS: AgentPreset[] = [
  {
    id: 'cigana',
    name: 'Cigana Spanda',
    role: 'Tarot, Áudios & Conversão Pix R$ 9,90',
    badge: '🔮 Oficial Meu Mistério',
    avatar: '#7c3aed',
    icon: '🔮',
    description: 'Atendimento místico, empático e acolhedor. Conduz o consulente pela revelação de 3 cartas e converte suavemente na leitura aprofundada via Pix.',
    highlights: ['Leitura de 3 cartas guiada', 'Tom de acolhimento espiritual', 'Conversão Pix R$ 9,90'],
    modelId: 'gemini-2.5-flash',
    draft: {
      model: 'gemini-2.5-flash',
      temperature: 0.4,
      delay_seconds: 3,
      personalidade:
        'Você é a Cigana Spanda, conselheira espiritual oficial do Meu Mistério. Fale com voz calorosa, compassiva, misteriosa e acolhedora. Trate o consulente carinhosamente como "meu bem", "minha flor" ou "meu querido". Crie um ambiente seguro, sem julgamentos morais e com profundo respeito às dores do coração.',
      instrucoes: `# IDENTIDADE E MISSÃO
Você é a Cigana Spanda, oraculista e conselheira do Meu Mistério. Você atende pessoas em busca de respostas no amor, nas finanças e nos caminhos espirituais.

# DIRETRIZES DE ATENDIMENTO
1. ACOLHIMENTO: Dê as boas-vindas com calor humano. Peça o primeiro nome e a principal dúvida que aflige o coração do consulente.
2. TIRAGEM DAS 3 CARTAS: Revele as 3 cartas (Passado / Presente / Caminho Futuro) com sabedoria ancestral, oferecendo clareza e conselhos práticos.
3. OFERTA DA LEITURA COMPLETA: Após a resposta inicial, explique com delicadeza que para desvendar todos os segredos do mapa energético e orientações completas, a consulta aprofundada custa apenas R$ 9,90 via Pix com liberação imediata.
4. COBRANÇA PIX: Forneça a chave Pix ou código de pagamento quando solicitado e oriente o envio do comprovante.

# LIMITES ÉTICOS INVIOLÁVEIS
- Nunca prometa amarração amorosa, feitiços de vingança ou prazos mágicos de 24h.
- Nunca faça diagnósticos médicos nem oriente interromper tratamentos de saúde.
- Seja sempre um farol de luz, esperança e responsabilidade.`,
      base_conhecimento: `SERVIÇOS E POLÍTICAS - MEU MISTÉRIO:
- Tiragem Inicial de Boas-Vindas: Gratuita (3 cartas).
- Consulta Completa Aprofundada com Cigana Spanda: R$ 9,90 via Pix.
- Chave Pix: pix@meumisterio.com.br (ou código copia-e-cola gerado automaticamente).
- Envio do Mapa & Previsões: Imediato pelo WhatsApp oficial assim que confirmado o pagamento.
- Horário de Atendimento: Disponível 24 horas por dia, todos os dias da semana.`,
      faqs: [
        {
          q: 'Quanto custa a consulta completa?',
          a: 'A leitura completa aprofundada custa apenas R$ 9,90 via Pix, meu bem! Posso gerar seu código com liberação imediata agora?',
        },
        {
          q: 'Vocês aceitam Pix?',
          a: 'Sim! Aceitamos Pix com aprovação imediata. Custa apenas R$ 9,90 e você recebe suas orientações completas na hora aqui no WhatsApp.',
        },
        {
          q: 'Como funciona a tiragem de tarot?',
          a: 'As cartas mostram as energias que estão ao seu redor agora: suas raízes, os desafios de hoje e o que está por vir. Me conte seu nome e o que mais preocupa seu coração!',
        },
      ],
    },
  },
  {
    id: 'vendas',
    name: 'Bia - Vendas & Conversão Pix',
    role: 'SDR & Fechamento Comercial Direto',
    badge: '💼 Alta Conversão',
    avatar: '#2563eb',
    icon: '💼',
    description: 'Atendente comercial persuasiva, ágil e focada em qualificar o lead, quebrar objeções de compra e enviar chaves Pix e links de checkout.',
    highlights: ['Qualificação rápida de dores', 'Quebra de objeções de preço', 'Links de pagamento e Pix'],
    modelId: 'gpt-4o-mini',
    draft: {
      model: 'gpt-4o-mini',
      temperature: 0.2,
      delay_seconds: 2,
      personalidade:
        'Você é a Bia, especialista em atendimento comercial e vendas. Fale com dinamismo, simpatia, objetividade e clareza. Use frases curtas (máximo 2 ou 3 linhas por bloco). Jamais envie textos gigantescos. Demonstre segurança e conduza o cliente para a decisão de compra.',
      instrucoes: `# OBJETIVO DO AGENTE
Seu papel é identificar o interesse do lead, esclarecer dúvidas pontuais e fechar vendas no menor tempo de conversa possível.

# ROTEIRO DE VENDAS
1. QUALIFICAÇÃO: Entenda o que o cliente procura com uma pergunta rápida.
2. APRESENTAÇÃO: Apresente a solução de forma personalizada destacando os principais benefícios.
3. CONDIÇÃO ESPECIAL: Apresente o preço e reforce a condição especial para pagamento imediato no Pix.
4. FECHAMENTO: Envie o link ou chave de pagamento e ofereça ajuda imediata para finalizar o pedido.

# REGRAS DE ATENDIMENTO
- Nunca discuta nem seja insistente de forma invasiva.
- Sempre use o primeiro nome do cliente.
- Se o cliente tiver dúvida de parcelamento, informe as opções em até 12x no cartão.`,
      base_conhecimento: `PLANOS E FORMAS DE PAGAMENTO:
- Plano Essencial: R$ 97/mês (Até 1 número de WhatsApp, 1.000 mensagens).
- Plano Pro Ilimitado: R$ 197/mês (Leads ilimitados, IA autônoma 24h, disparos em massa).
- Formas de Pagamento: Pix à vista com liberação imediata ou Cartão de Crédito em até 12x.
- Garantia: 7 dias incondicionais com reembolso integral em até 24 horas úteis.`,
      faqs: [
        {
          q: 'Tem desconto para pagamento no Pix?',
          a: 'Com certeza! No Pix à vista liberamos sua conta imediatamente com condição especial. Quer que eu te envie o link agora?',
        },
        {
          q: 'Como funciona a garantia de 7 dias?',
          a: 'Você pode testar tudo por 7 dias. Se não gostar por qualquer motivo, basta nos mandar uma mensagem que devolvemos 100% do seu dinheiro.',
        },
        {
          q: 'Posso parcelar no cartão?',
          a: 'Sim! Parcelamos em até 12x no cartão de crédito com aprovação na hora.',
        },
      ],
    },
  },
  {
    id: 'suporte',
    name: 'Carlos - Suporte & Triagem Humanizada',
    role: 'Atendimento ao Cliente & SAC 24h',
    badge: '🎧 Retenção & CS',
    avatar: '#059669',
    icon: '🎧',
    description: 'Atendente de suporte paciente, empático e resolutivo. Responde dúvidas frequentes em segundos e faz transbordo suave para atendentes humanos.',
    highlights: ['Resolução de dúvidas em 3s', 'Coleta de dados do chamado', 'Transbordo humano suave'],
    modelId: 'gemini-2.5-flash',
    draft: {
      model: 'gemini-2.5-flash',
      temperature: 0.1,
      delay_seconds: 2,
      personalidade:
        'Você é o Carlos, especialista do time de suporte ao cliente. Fale com muita educação, respeito, empatia e clareza. Use uma linguagem simples, acolhedora e sem termos técnicos desnecessários.',
      instrucoes: `# DIRETRIZES DO SUPORTE
1. RECEPÇÃO: Cumprimente o cliente com cordialidade e pergunte em que pode ajudar hoje.
2. RESOLUÇÃO: Consulte a base de dados interna e oriente o cliente com passos simples e numerados.
3. CONFIRMAÇÃO: Pergunte se a dúvida foi sanada com sucesso.
4. TRANSBORDO HUMANO: Caso o cliente diga "quero falar com atendente", "humano", "pessoa real" ou se o problema não tiver solução nos dados, responda imediatamente: "Com certeza! Estou transferindo seu atendimento para a nossa equipe humana agora mesmo. Um momento, por favor!"`,
      base_conhecimento: `HORÁRIOS DE ATENDIMENTO E POLÍTICAS:
- Suporte Humano: Segunda a Sexta das 08h às 20h. Sábados das 09h às 14h.
- Atendimento via IA: 24 horas por dia, 7 dias por semana.
- 2ª via de faturas e comprovantes: Enviadas automaticamente para o e-mail do titular.
- Prazos de cancelamento: Solicitações processadas em até 24 horas úteis.`,
      faqs: [
        {
          q: 'Como falo com um atendente humano?',
          a: 'Com certeza! Estou transferindo seu atendimento para a nossa equipe agora mesmo. Aguarde um instante que um de nossos consultores vai te responder aqui.',
        },
        {
          q: 'Não recebi o acesso, o que fazer?',
          a: 'Por favor, confira a sua caixa de spam e promoções. Se não localizar, me confirme seu e-mail cadastrado que verifico no sistema para você agora!',
        },
        {
          q: 'Qual o prazo de reembolso?',
          a: 'Os reembolsos dentro da garantia de 7 dias são processados em até 24 horas úteis para a mesma chave Pix ou fatura do cartão.',
        },
      ],
    },
  },
  {
    id: 'custom',
    name: 'Assistente Personalizado',
    role: 'Configuração Livre & Rascunho Limpo',
    badge: '⚡ Do Zero',
    avatar: '#4f46e5',
    icon: '⚡',
    description: 'Comece do zero com sua própria identidade visual, regras de prompt, catálogo de produtos e perguntas frequentes.',
    highlights: ['Prompt 100% customizável', 'Qualquer motor de IA', 'Sem textos pré-definidos'],
    modelId: 'gemini-2.5-flash',
    draft: {
      model: 'gemini-2.5-flash',
      temperature: 0.3,
      delay_seconds: 3,
      personalidade: '',
      instrucoes: '',
      base_conhecimento: '',
      faqs: [],
    },
  },
];

export default function AgentStudio() {
  const qc = useQueryClient();
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [initialPresetId, setInitialPresetId] = useState<string>('cigana');
  const [agentToDelete, setAgentToDelete] = useState<AgentSummary | null>(null);

  const { data: agents = [], isLoading } = useQuery({
    queryKey: ['studio-agents'],
    queryFn: agentsApi.list,
  });

  const { data: pubStatus } = useQuery({
    queryKey: ['studio-publish-status'],
    queryFn: agentsApi.publishStatus,
  });

  // Auto-seleciona o primeiro agente se nenhum selecionado
  useEffect(() => {
    if (selectedId == null && agents.length > 0) setSelectedId(agents[0].id);
  }, [agents, selectedId]);

  const createMutation = useMutation({
    mutationFn: agentsApi.create,
    onSuccess: (res) => {
      toast.success('Novo atendente de IA criado com sucesso!');
      qc.invalidateQueries({ queryKey: ['studio-agents'] });
      setSelectedId(res.agent.id);
      setIsCreateOpen(false);
    },
    onError: (e) => toast.error((e as Error).message),
  });

  const removeMutation = useMutation({
    mutationFn: agentsApi.remove,
    onSuccess: () => {
      toast.success('Atendente removido com sucesso.');
      qc.invalidateQueries({ queryKey: ['studio-agents'] });
      setAgentToDelete(null);
      setSelectedId(null);
    },
    onError: (e) => toast.error((e as Error).message),
  });

  const handleOpenCreate = (presetId: string = 'cigana') => {
    setInitialPresetId(presetId);
    setIsCreateOpen(true);
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
            onClick={() => handleOpenCreate('cigana')}
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
              Carregando atendentes de IA…
            </div>
          )}

          {!isLoading && agents.length === 0 && (
            <div className="p-6 text-center space-y-3">
              <div className="w-12 h-12 rounded-2xl bg-zinc-800/60 border border-zinc-700/50 flex items-center justify-center mx-auto text-zinc-500">
                <Bot className="w-6 h-6" />
              </div>
              <p className="text-xs text-zinc-400 font-medium leading-relaxed">
                Nenhum atendente cadastrado ainda.
              </p>
              <button
                onClick={() => handleOpenCreate('cigana')}
                className="w-full text-xs font-bold py-2 rounded-xl bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 flex items-center justify-center gap-1.5 transition-all"
              >
                <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                Criar Primeiro Atendente
              </button>
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
            onDelete={() => setAgentToDelete(selectedAgent)}
          />
        ) : (
          <EmptyStateHero onSelectPreset={(presetId) => handleOpenCreate(presetId)} />
        )}
      </main>

      {/* ═══ MODAIS PERSONALIZADOS (ZERO WINDOW.PROMPT / CONFIRM) ═══ */}
      {isCreateOpen && (
        <CreateAgentModal
          initialPresetId={initialPresetId}
          onClose={() => setIsCreateOpen(false)}
          isPending={createMutation.isPending}
          onSubmit={(data) => createMutation.mutate(data)}
        />
      )}

      {agentToDelete && (
        <DeleteAgentModal
          agent={agentToDelete}
          onClose={() => setAgentToDelete(null)}
          onConfirm={() => removeMutation.mutate(agentToDelete.id)}
          isPending={removeMutation.isPending}
        />
      )}
    </div>
  );
}

// ── EMPTY STATE HERO COM TEMPLATES PRONTOS ────────────────────────────

function EmptyStateHero({ onSelectPreset }: { onSelectPreset: (presetId: string) => void }) {
  return (
    <div className="h-full flex flex-col items-center justify-center p-8 max-w-5xl mx-auto space-y-8 animate-in fade-in duration-300">
      <div className="text-center space-y-3 max-w-2xl">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 text-xs font-bold uppercase tracking-wider shadow-sm">
          <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
          Estúdio de Inteligência Artificial WhatsApp
        </div>
        <h2 className="text-2xl md:text-3xl font-black text-zinc-100 tracking-tight">
          Crie seu Atendente de IA em Segundos
        </h2>
        <p className="text-sm text-zinc-400 leading-relaxed">
          Chega de telas em branco. Selecione um dos modelos especializados abaixo ou crie seu agente customizado pronto para responder ao vivo no WhatsApp oficial.
        </p>
      </div>

      {/* Grid de Templates de Alta Conversão */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5 w-full">
        {AGENT_PRESETS.filter((p) => p.id !== 'custom').map((p) => (
          <div
            key={p.id}
            className="group relative bg-zinc-900/70 hover:bg-zinc-900 border border-zinc-800 hover:border-indigo-500/50 rounded-2xl p-5 flex flex-col justify-between transition-all duration-200 hover:shadow-xl hover:shadow-indigo-500/5 hover:-translate-y-1"
          >
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div
                  className="w-12 h-12 rounded-2xl flex items-center justify-center text-xl shadow-lg border border-white/10"
                  style={{ backgroundColor: p.avatar }}
                >
                  {p.icon}
                </div>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-300 border border-zinc-700">
                  {p.badge}
                </span>
              </div>

              <div>
                <h3 className="text-base font-black text-zinc-100 group-hover:text-indigo-300 transition-colors">
                  {p.name}
                </h3>
                <p className="text-xs font-semibold text-zinc-400 mt-0.5">{p.role}</p>
                <p className="text-xs text-zinc-400 leading-relaxed mt-2.5">{p.description}</p>
              </div>

              <div className="space-y-1.5 pt-3 border-t border-zinc-800/80">
                {p.highlights.map((h, i) => (
                  <div key={i} className="flex items-center gap-2 text-[11px] text-zinc-300">
                    <Check className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
                    <span>{h}</span>
                  </div>
                ))}
              </div>
            </div>

            <button
              onClick={() => onSelectPreset(p.id)}
              className="mt-6 w-full py-2.5 rounded-xl bg-zinc-800 hover:bg-indigo-600 text-zinc-200 hover:text-white text-xs font-bold transition-all flex items-center justify-center gap-2 group-hover:shadow-md group-hover:shadow-indigo-600/20"
            >
              <Wand2 className="w-3.5 h-3.5" />
              Usar Este Modelo
            </button>
          </div>
        ))}
      </div>

      <div className="pt-2">
        <button
          onClick={() => onSelectPreset('custom')}
          className="text-xs font-bold text-zinc-400 hover:text-indigo-300 flex items-center gap-1.5 transition-colors underline-offset-4 hover:underline"
        >
          <Zap className="w-3.5 h-3.5 text-indigo-400" />
          Ou criar um atendente em branco (personalizado) →
        </button>
      </div>
    </div>
  );
}

// ── MODAL WIZARD: NOVO ATENDENTE DE IA ─────────────────────────────────

function CreateAgentModal({
  initialPresetId,
  onClose,
  onSubmit,
  isPending,
}: {
  initialPresetId: string;
  onClose: () => void;
  onSubmit: (data: { name: string; avatar: string; draft: AgentDraft }) => void;
  isPending: boolean;
}) {
  const [selectedPresetId, setSelectedPresetId] = useState(initialPresetId);
  const activePreset = AGENT_PRESETS.find((p) => p.id === selectedPresetId) || AGENT_PRESETS[0];

  const [name, setName] = useState(activePreset.name);
  const [avatar, setAvatar] = useState(activePreset.avatar);
  const [selectedModel, setSelectedModel] = useState(activePreset.modelId);

  // Atualiza nome e cor ao trocar preset
  const handleSelectPreset = (p: AgentPreset) => {
    setSelectedPresetId(p.id);
    setName(p.name);
    setAvatar(p.avatar);
    setSelectedModel(p.modelId);
  };

  const handleConfirm = () => {
    if (!name.trim()) {
      toast.error('Informe um nome para o atendente de IA.');
      return;
    }
    const finalDraft: AgentDraft = {
      ...activePreset.draft,
      model: selectedModel,
    };
    onSubmit({
      name: name.trim(),
      avatar,
      draft: finalDraft,
    });
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto animate-in fade-in duration-200">
      <div className="bg-zinc-900 border border-zinc-800 rounded-3xl p-6 md:p-8 max-w-2xl w-full shadow-2xl space-y-6 animate-in zoom-in-95 duration-200 max-h-[90vh] overflow-y-auto">
        {/* Cabeçalho */}
        <div className="flex items-center justify-between pb-4 border-b border-zinc-800">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-black text-zinc-100">Novo Atendente de IA</h3>
              <p className="text-xs text-zinc-400">
                Escolha uma persona pronta de alta conversão ou monte a sua do zero.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 transition-all"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Escolha do Template / Preset */}
        <div className="space-y-2">
          <label className="text-xs font-bold uppercase tracking-wider text-zinc-400 block">
            1. Selecione o Modelo Base
          </label>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {AGENT_PRESETS.map((p) => {
              const isSelected = selectedPresetId === p.id;
              return (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => handleSelectPreset(p)}
                  className={`text-left p-3.5 rounded-2xl border transition-all flex items-start gap-3 ${
                    isSelected
                      ? 'bg-indigo-500/10 border-indigo-500/60 ring-1 ring-indigo-500/30'
                      : 'bg-zinc-950/60 border-zinc-800 hover:border-zinc-700'
                  }`}
                >
                  <div
                    className="w-10 h-10 rounded-xl flex items-center justify-center text-lg shadow flex-shrink-0"
                    style={{ backgroundColor: p.avatar }}
                  >
                    {p.icon}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-zinc-100 truncate">{p.name}</span>
                      {isSelected && <Check className="w-3.5 h-3.5 text-indigo-400 flex-shrink-0" />}
                    </div>
                    <span className="text-[10px] text-zinc-400 line-clamp-2 mt-0.5 leading-snug">
                      {p.role}
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Nome do Atendente & Identidade */}
        <div className="space-y-4 pt-2 border-t border-zinc-800/80">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="sm:col-span-2 space-y-1.5">
              <label className="text-xs font-bold uppercase tracking-wider text-zinc-400 block">
                2. Nome do Atendente
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Ex: Bia - Vendas, Cigana Spanda, Carlos"
                className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-4 py-2.5 text-sm text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-indigo-500 transition-all font-bold"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-bold uppercase tracking-wider text-zinc-400 block">
                Cor do Avatar
              </label>
              <div className="flex items-center gap-2 pt-1">
                {AVATAR_COLORS.map((c) => (
                  <button
                    key={c}
                    type="button"
                    onClick={() => setAvatar(c)}
                    className={`w-7 h-7 rounded-xl transition-all ${
                      avatar === c ? 'ring-2 ring-white ring-offset-2 ring-offset-zinc-900 scale-110' : 'opacity-70 hover:opacity-100'
                    }`}
                    style={{ backgroundColor: c }}
                  />
                ))}
              </div>
            </div>
          </div>

          {/* Motor de IA */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold uppercase tracking-wider text-zinc-400 block">
              3. Motor de Inteligência Artificial
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {AI_MODELS.map((m) => {
                const isSelected = selectedModel === m.id;
                return (
                  <button
                    key={m.id}
                    type="button"
                    onClick={() => setSelectedModel(m.id)}
                    className={`p-2.5 rounded-xl border text-left transition-all ${
                      isSelected
                        ? 'bg-indigo-500/15 border-indigo-500/60 ring-1 ring-indigo-500/20'
                        : 'bg-zinc-950/60 border-zinc-800 hover:border-zinc-700'
                    }`}
                  >
                    <div className="text-[11px] font-bold text-zinc-200 truncate">{m.name}</div>
                    <div className="text-[10px] text-zinc-500 mt-0.5">{m.badge}</div>
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Rodapé e Botões */}
        <div className="flex items-center justify-end gap-3 pt-4 border-t border-zinc-800">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2.5 rounded-xl text-xs font-bold text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition-all"
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={handleConfirm}
            disabled={isPending || !name.trim()}
            className="px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-xs font-bold transition-all shadow-md shadow-indigo-600/30 flex items-center gap-2 active:scale-95"
          >
            <Wand2 className="w-4 h-4" />
            {isPending ? 'Criando Atendente…' : 'Criar Atendente de IA'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── MODAL: EXCLUIR AGENTE (SUBSTITUTO SLEEK DE CONFIRM) ─────────────────

function DeleteAgentModal({
  agent,
  onClose,
  onConfirm,
  isPending,
}: {
  agent: AgentSummary;
  onClose: () => void;
  onConfirm: () => void;
  isPending: boolean;
}) {
  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in duration-200">
      <div className="bg-zinc-900 border border-zinc-800 rounded-3xl p-6 max-w-md w-full shadow-2xl space-y-5 animate-in zoom-in-95 duration-200">
        <div className="w-12 h-12 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center justify-center text-red-400 mx-auto">
          <AlertTriangle className="w-6 h-6" />
        </div>

        <div className="text-center space-y-2">
          <h3 className="text-lg font-black text-zinc-100">Excluir Atendente de IA?</h3>
          <p className="text-xs text-zinc-400 leading-relaxed">
            Tem certeza que deseja apagar o atendente <strong className="text-zinc-200">"{agent.name}"</strong>?
            Esta ação é irreversível e removerá todas as diretrizes de prompt e versões congeladas.
          </p>
        </div>

        <div className="flex items-center justify-end gap-3 pt-2">
          <button
            onClick={onClose}
            className="flex-1 py-2.5 rounded-xl text-xs font-bold text-zinc-400 hover:text-zinc-200 bg-zinc-800 hover:bg-zinc-700 transition-all"
          >
            Cancelar
          </button>
          <button
            onClick={onConfirm}
            disabled={isPending}
            className="flex-1 py-2.5 rounded-xl bg-red-600 hover:bg-red-500 text-white text-xs font-bold transition-all shadow-md shadow-red-600/30 flex items-center justify-center gap-1.5"
          >
            <Trash2 className="w-3.5 h-3.5" />
            {isPending ? 'Excluindo…' : 'Sim, Excluir'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── MODAL: CONGELAR VERSÃO (SUBSTITUTO SLEEK DE WINDOW.PROMPT) ─────────

function FreezeVersionModal({
  onClose,
  onConfirm,
  isPending,
}: {
  onClose: () => void;
  onConfirm: (note: string) => void;
  isPending: boolean;
}) {
  const [note, setNote] = useState('');

  const quickTags = [
    'Prompt ajustado para fechar mais vendas',
    'Atualização de preços Pix',
    'Ajuste no acolhimento de Tarot',
    'Versão estável validada',
  ];

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in duration-200">
      <div className="bg-zinc-900 border border-zinc-800 rounded-3xl p-6 md:p-7 max-w-lg w-full shadow-2xl space-y-5 animate-in zoom-in-95 duration-200">
        <div className="flex items-center justify-between pb-3 border-b border-zinc-800">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
              <Camera className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-black text-zinc-100">Congelar Nova Versão</h3>
              <p className="text-xs text-zinc-400">
                Gere um ponto de restauração imutável para publicar no WhatsApp.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="space-y-2">
          <label className="text-xs font-bold uppercase tracking-wider text-zinc-400 block">
            Descrição / Nota da Versão
          </label>
          <input
            type="text"
            autoFocus
            value={note}
            onChange={(e) => setNote(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && onConfirm(note)}
            placeholder="Ex: Prompt ajustado para fechar vendas no WhatsApp..."
            className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-4 py-2.5 text-xs text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-indigo-500 transition-all font-medium"
          />

          <div className="pt-2 space-y-1.5">
            <span className="text-[10px] uppercase font-bold text-zinc-500">Sugestões rápidas:</span>
            <div className="flex flex-wrap gap-1.5">
              {quickTags.map((tag) => (
                <button
                  key={tag}
                  type="button"
                  onClick={() => setNote(tag)}
                  className="text-[11px] px-2.5 py-1 rounded-lg bg-zinc-800/80 hover:bg-zinc-700 text-zinc-300 hover:text-white transition-all border border-zinc-700/50"
                >
                  {tag}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="flex items-center justify-end gap-3 pt-3 border-t border-zinc-800">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-xs font-bold text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition-all"
          >
            Cancelar
          </button>
          <button
            onClick={() => onConfirm(note)}
            disabled={isPending}
            className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold transition-all shadow-md shadow-indigo-600/30 flex items-center gap-1.5"
          >
            <Camera className="w-3.5 h-3.5" />
            {isPending ? 'Congelando…' : 'Salvar & Congelar'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── MODAL: PUBLICAR NO WHATSAPP (SUBSTITUTO SLEEK DE CONFIRM) ──────────

function PublishVersionModal({
  version,
  onClose,
  onConfirm,
  isPending,
}: {
  version: { id: number; version_number: number; note?: string | null };
  onClose: () => void;
  onConfirm: () => void;
  isPending: boolean;
}) {
  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in duration-200">
      <div className="bg-zinc-900 border border-zinc-800 rounded-3xl p-6 md:p-7 max-w-md w-full shadow-2xl space-y-5 animate-in zoom-in-95 duration-200">
        <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 mx-auto">
          <Rocket className="w-6 h-6" />
        </div>

        <div className="text-center space-y-2">
          <h3 className="text-lg font-black text-zinc-100">Ativar no WhatsApp Oficial?</h3>
          <p className="text-xs text-zinc-400 leading-relaxed">
            Deseja publicar e colocar ao vivo a <strong className="text-zinc-200">Versão #{version.version_number}</strong>
            {version.note ? ` ("${version.note}")` : ''}?
            Ela responderá imediatamente a todas as conversas do seu WhatsApp oficial.
          </p>
        </div>

        <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-xl flex items-center gap-2 text-xs text-emerald-300 font-medium">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
          <span>Ativação instantânea no motor do WhatsApp oficial</span>
        </div>

        <div className="flex items-center justify-end gap-3 pt-2">
          <button
            onClick={onClose}
            className="flex-1 py-2.5 rounded-xl text-xs font-bold text-zinc-400 hover:text-zinc-200 bg-zinc-800 hover:bg-zinc-700 transition-all"
          >
            Cancelar
          </button>
          <button
            onClick={onConfirm}
            disabled={isPending}
            className="flex-1 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold transition-all shadow-md shadow-emerald-600/30 flex items-center justify-center gap-1.5"
          >
            <Rocket className="w-3.5 h-3.5" />
            {isPending ? 'Ativando…' : 'Publicar ao Vivo'}
          </button>
        </div>
      </div>
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

  // Estados dos novos modais elegantes
  const [isFreezeOpen, setIsFreezeOpen] = useState(false);
  const [versionToPublish, setVersionToPublish] = useState<{
    id: number;
    version_number: number;
    note?: string | null;
  } | null>(null);

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
      toast.success('Configurações salvas com sucesso.');
      qc.invalidateQueries({ queryKey: ['studio-agents'] });
    },
    onError: (e) => toast.error((e as Error).message),
  });

  const snapshotMutation = useMutation({
    mutationFn: (note: string) => agentsApi.snapshot(agent.id, note),
    onSuccess: () => {
      toast.success('Versão congelada criada com sucesso!');
      setIsFreezeOpen(false);
      qc.invalidateQueries({ queryKey: ['studio-agents'] });
    },
    onError: (e) => toast.error((e as Error).message),
  });

  const publishMutation = useMutation({
    mutationFn: (versionId: number) => agentsApi.publish(agent.id, versionId),
    onSuccess: (res) => {
      toast.success(`Versão #${res.published_version_id} ativada para o WhatsApp oficial!`);
      setVersionToPublish(null);
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
                ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40 shadow-sm'
                : 'bg-zinc-850 border-zinc-700/80 text-zinc-300 hover:text-white hover:bg-zinc-800'
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
            onClick={() => setIsFreezeOpen(true)}
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
            title="Excluir atendente"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* ═══ SIMULADOR DO WHATSAPP (SE ATIVO) ═══ */}
      {showSimulator && (
        <WhatsAppSimulator
          agentName={name}
          instructions={(draft.instrucoes as string) || ''}
          knowledge={(draft.base_conhecimento as string) || ''}
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
                <h4 className="text-sm font-bold text-zinc-200">Histórico de Versões do Atendente</h4>
                <p className="text-xs text-zinc-400">
                  Cada snapshot é uma cópia segura e imutável. Você pode ativar qualquer versão anterior a qualquer momento.
                </p>
              </div>
              <button
                onClick={() => setIsFreezeOpen(true)}
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
                          onClick={() => setVersionToPublish(v)}
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

      {/* Modais de Versão e Publicação */}
      {isFreezeOpen && (
        <FreezeVersionModal
          onClose={() => setIsFreezeOpen(false)}
          onConfirm={(note) => snapshotMutation.mutate(note)}
          isPending={snapshotMutation.isPending}
        />
      )}

      {versionToPublish && (
        <PublishVersionModal
          version={versionToPublish}
          onClose={() => setVersionToPublish(null)}
          onConfirm={() => publishMutation.mutate(versionToPublish.id)}
          isPending={publishMutation.isPending}
        />
      )}
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
  const initialGreeting = `Olá! Sou ${agentName || 'o assistente virtual'}. Como posso te ajudar hoje?`;
  const [messages, setMessages] = useState<{ sender: 'user' | 'bot'; text: string; time: string }[]>([
    {
      sender: 'bot',
      text: initialGreeting,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  const handleSend = (customText?: string) => {
    const userMsg = (customText ?? input).trim();
    if (!userMsg || isTyping) return;
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    setMessages((prev) => [...prev, { sender: 'user', text: userMsg, time }]);
    if (!customText) setInput('');
    setIsTyping(true);

    // Simulação inteligente baseada em FAQs locais ou prompt
    setTimeout(() => {
      let botResponse = '';
      const matchedFaq = faqs.find((f) =>
        f.q && userMsg.toLowerCase().includes(f.q.toLowerCase().slice(0, 12))
      );

      if (matchedFaq && matchedFaq.a) {
        botResponse = matchedFaq.a;
      } else if (knowledge && knowledge.toLowerCase().includes(userMsg.toLowerCase().slice(0, 10))) {
        botResponse = `Com base nas informações cadastradas: temos exatamente o que você procura! Quer que eu te envie o link direto para contratação?`;
      } else if (userMsg.toLowerCase().includes('preço') || userMsg.toLowerCase().includes('valor')) {
        botResponse = `A consulta completa custa apenas R$ 9,90 via Pix com liberação imediata. Deseja que eu gere o seu código Pix agora?`;
      } else {
        botResponse = `Entendido! Estou respondendo conforme as diretrizes do seu atendente de IA. Posso te ajudar com algo mais específico?`;
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
    }, 1100);
  };

  const handleReset = () => {
    setMessages([
      {
        sender: 'bot',
        text: initialGreeting,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      },
    ]);
  };

  return (
    <div className="bg-[#0b141a] border border-zinc-800 rounded-2xl overflow-hidden shadow-2xl transition-all animate-in fade-in duration-200">
      {/* WhatsApp Header */}
      <div className="bg-[#202c33] px-4 py-3 flex items-center justify-between border-b border-zinc-800">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-[#25D366] flex items-center justify-center text-sm font-black text-white shadow-md">
            {agentName.charAt(0).toUpperCase() || 'A'}
          </div>
          <div>
            <div className="text-sm font-bold text-zinc-100 flex items-center gap-2">
              <span>{agentName}</span>
              <span className="text-[10px] px-1.5 py-0.2 rounded bg-emerald-500/20 text-emerald-400 font-mono">
                Simulador Oficial
              </span>
            </div>
            <div className="text-[10px] text-emerald-400 flex items-center gap-1 font-medium">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              online no WhatsApp
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleReset}
            className="p-1.5 text-zinc-400 hover:text-zinc-100 rounded-lg hover:bg-zinc-700/60 transition-all"
            title="Reiniciar conversa"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
          <button
            onClick={onClose}
            className="text-xs text-zinc-300 hover:text-white px-2.5 py-1 rounded-lg bg-zinc-800 hover:bg-zinc-700 transition-all font-bold"
          >
            Fechar
          </button>
        </div>
      </div>

      {/* WhatsApp Chat Area */}
      <div className="h-80 p-4 overflow-y-auto space-y-3 bg-[#0b141a] bg-[radial-gradient(#182229_1px,transparent_1px)] [background-size:16px_16px]">
        {messages.map((m, i) => (
          <div
            key={i}
            className={`flex flex-col ${m.sender === 'user' ? 'items-end' : 'items-start'}`}
          >
            <div
              className={`max-w-[82%] rounded-2xl px-4 py-2.5 text-xs shadow-md ${
                m.sender === 'user'
                  ? 'bg-[#005c4b] text-white rounded-br-none'
                  : 'bg-[#202c33] text-zinc-100 rounded-bl-none'
              }`}
            >
              <p className="leading-relaxed whitespace-pre-wrap">{m.text}</p>
              <div className="flex items-center justify-end gap-1 mt-1 font-mono text-[9px] text-zinc-400">
                <span>{m.time}</span>
                {m.sender === 'user' && (
                  <span className="text-[#53bdeb] font-bold">✓✓</span>
                )}
              </div>
            </div>
          </div>
        ))}

        {isTyping && (
          <div className="flex items-center gap-1.5 bg-[#202c33] text-zinc-400 text-xs px-3.5 py-2 rounded-2xl rounded-bl-none w-fit shadow-md">
            <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-bounce" />
            <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-bounce [animation-delay:0.2s]" />
            <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-bounce [animation-delay:0.4s]" />
            <span className="text-[10px] text-emerald-400 font-medium ml-1">digitando...</span>
          </div>
        )}
        <div ref={endRef} />
      </div>

      {/* Quick Suggestions Chips */}
      <div className="px-3 py-2 bg-[#111b21] border-t border-zinc-800 flex items-center gap-1.5 overflow-x-auto">
        <span className="text-[10px] font-bold text-zinc-500 uppercase shrink-0">Testes rápidos:</span>
        {['Oi, como funciona?', 'Qual o valor da consulta?', 'Aceita Pix?'].map((suggestion) => (
          <button
            key={suggestion}
            type="button"
            onClick={() => handleSend(suggestion)}
            className="text-[11px] px-2.5 py-1 rounded-full bg-zinc-800 hover:bg-zinc-700 text-zinc-300 hover:text-white shrink-0 transition-colors border border-zinc-700/60"
          >
            {suggestion}
          </button>
        ))}
      </div>

      {/* WhatsApp Input Footer */}
      <div className="bg-[#202c33] p-3 flex items-center gap-2 border-t border-zinc-800">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder="Digite uma mensagem como cliente..."
          className="flex-1 bg-[#2a3942] border border-transparent focus:border-[#25D366] rounded-xl px-4 py-2.5 text-xs text-zinc-100 placeholder:text-zinc-400 focus:outline-none transition-all"
        />
        <button
          onClick={() => handleSend()}
          disabled={!input.trim() || isTyping}
          className="w-10 h-10 rounded-xl bg-[#00a884] hover:bg-[#008f6f] disabled:opacity-40 text-white flex items-center justify-center transition-all shadow-md active:scale-95 shrink-0"
        >
          <Send className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
