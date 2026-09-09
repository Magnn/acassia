import { useMemo, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import {
  Workflow,
  Plus,
  Search,
  Upload,
  Sparkles,
  ArrowRight,
  MoreVertical,
  CheckCircle2,
  Clock,
  Trash2,
  Copy,
  Download,
  Calendar,
  Layers,
  MessageSquare,
  HelpCircle,
  X,
  LogIn,
} from 'lucide-react';
import { blueprintsApi, type BlueprintSummary } from '../api/blueprints';
import { importBlueprintFromFile } from '../lib/exportImport';
import { toast } from '../lib/toast';

// Modelos pré-definidos de inicialização rápida
const STARTER_TEMPLATES = [
  {
    id: 'meu_misterio',
    title: 'Funil Meu Mistério (Tarot & Pix)',
    desc: '7 etapas completas: acolhimento da Cigana, áudios, tiragem de cartas e checkout de R$ 9,90 via Pix.',
    badge: '⚡ Meu Mistério Oficial',
    color: 'from-emerald-500/20 to-teal-500/20 border-emerald-500/30',
  },
  {
    id: 'comercial',
    title: 'Funil Comercial & Vendas',
    desc: 'Apresentação de produtos, qualificação de interesse e direcionamento para fechamento.',
    badge: 'Mais Popular',
    color: 'from-indigo-500/20 to-purple-500/20 border-indigo-500/30',
  },
  {
    id: 'agendamento',
    title: 'Agendamento & Triagem',
    desc: 'Coleta dados do cliente, tira dúvidas básicas e agenda horários de atendimento.',
    badge: 'Serviços & Clínicas',
    color: 'from-emerald-500/20 to-teal-500/20 border-emerald-500/30',
  },
  {
    id: 'atendente_ia',
    title: 'Assistente IA com Transbordo',
    desc: 'Atendimento 24/7 com IA personalizada e repasse para atendente humano quando necessário.',
    badge: 'Inteligência Artificial',
    color: 'from-blue-500/20 to-cyan-500/20 border-blue-500/30',
  },
];

export default function BlueprintsList() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const fileRef = useRef<HTMLInputElement | null>(null);

  const [searchQuery, setSearchQuery] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [showTemplates, setShowTemplates] = useState(false);
  const [newFlowTitle, setNewFlowTitle] = useState('');
  const [activeMenuId, setActiveMenuId] = useState<number | null>(null);

  // Consulta de Blueprints do Tenant
  const { data: blueprints = [], isLoading, error } = useQuery({
    queryKey: ['blueprints'],
    queryFn: blueprintsApi.list,
  });

  // Consulta do status de publicação
  const { data: publishStatus } = useQuery({
    queryKey: ['publishStatus'],
    queryFn: blueprintsApi.publishStatus,
  });

  const publishedId = publishStatus?.published?.blueprint_id ?? null;

  // Mutação para criar novo fluxo
  const { mutate: createBlueprint, isPending: isCreating } = useMutation({
    mutationFn: blueprintsApi.create,
    onSuccess: (bp: BlueprintSummary) => {
      qc.invalidateQueries({ queryKey: ['blueprints'] });
      toast.success('Fluxo criado com sucesso!');
      navigate(`/flows/${bp.id}`);
    },
    onError: (err: Error) => {
      toast.error(err.message || 'Erro ao criar fluxo');
    },
  });

  // Importar arquivo JSON
  const onPickFile = async (file: File) => {
    try {
      const newId = await importBlueprintFromFile(file);
      if (newId) {
        qc.invalidateQueries({ queryKey: ['blueprints'] });
        toast.success('Fluxo importado com sucesso!');
        navigate(`/flows/${newId}`);
      }
    } catch {
      toast.error('Arquivo de fluxo inválido.');
    }
  };

  // Filtragem por busca
  const filteredBlueprints = useMemo(() => {
    if (!searchQuery.trim()) return blueprints;
    const q = searchQuery.toLowerCase();
    return blueprints.filter(
      (b) => b.title.toLowerCase().includes(q) || b.slug.toLowerCase().includes(q)
    );
  }, [blueprints, searchQuery]);

  // Criar a partir de modelo starter
  const handleUseTemplate = (tmpl: typeof STARTER_TEMPLATES[0]) => {
    createBlueprint({
      title: tmpl.title,
      integration: 'whatsapp',
      event: 'message',
    });
  };

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* ═══ HEADER DA PÁGINA ═══ */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-bold text-white tracking-tight">Fluxos de Conversa</h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-zinc-800 text-zinc-300 border border-zinc-700/60">
              {blueprints.length} {blueprints.length === 1 ? 'fluxo' : 'fluxos'}
            </span>
          </div>
          <p className="text-xs sm:text-sm text-zinc-400 mt-1">
            Construa, simule e publique automações visuais com IA conectadas ao WhatsApp Meta.
          </p>
        </div>

        {/* Botões de Ação no padrão ChatbotX/Linear */}
        <div className="flex items-center gap-2.5">
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold bg-zinc-900 border border-zinc-800 text-zinc-200 hover:bg-zinc-800 hover:text-white transition-all shadow-sm"
          >
            <Upload className="w-3.5 h-3.5 text-zinc-400" />
            <span>Importar JSON</span>
          </button>

          <input
            ref={fileRef}
            type="file"
            accept="application/json,.json"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) onPickFile(f);
              e.target.value = '';
            }}
          />

          <button
            type="button"
            onClick={() => {
              setNewFlowTitle('');
              setIsModalOpen(true);
            }}
            disabled={isCreating}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold bg-gradient-to-r from-indigo-600 via-indigo-500 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white transition-all shadow-md shadow-indigo-600/20 active:scale-[0.98]"
          >
            <Plus className="w-4 h-4" />
            <span>Novo Fluxo</span>
          </button>
        </div>
      </div>

      {/* ═══ BARRA DE BUSCA & FILTRO ═══ */}
      {blueprints.length > 0 && (
        <div className="mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="relative flex-1 max-w-md">
            <Search className="w-4 h-4 text-zinc-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Buscar fluxos por nome ou slug..."
              className="w-full pl-10 pr-4 py-2 bg-zinc-900/70 border border-zinc-800/80 rounded-xl text-xs sm:text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 transition-all"
            />
          </div>
          <button
            type="button"
            onClick={() => setShowTemplates((v) => !v)}
            className={`inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold border transition-all ${
              showTemplates
                ? 'bg-indigo-600/20 border-indigo-500/40 text-indigo-300'
                : 'bg-zinc-900 border-zinc-800 text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
            <span>{showTemplates ? 'Ocultar Modelos' : 'Explorar Modelos Prontos'}</span>
          </button>
        </div>
      )}

      {/* Grid de Modelos quando toggle ativo */}
      {showTemplates && blueprints.length > 0 && (
        <div className="mb-8 p-5 bg-zinc-900/40 border border-zinc-800 rounded-2xl animate-in fade-in duration-200">
          <div className="flex items-center gap-2 mb-4">
            <Layers className="w-4 h-4 text-indigo-400" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-300">
              Modelos Prontos de Inicialização Rápida
            </h3>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3.5">
            {STARTER_TEMPLATES.map((tmpl) => (
              <div
                key={tmpl.id}
                className="p-4 rounded-xl bg-zinc-900/70 border border-zinc-800 hover:border-zinc-700 flex flex-col justify-between transition-all group"
              >
                <div>
                  <span className="inline-block px-2 py-0.5 rounded-full text-[9px] font-bold bg-zinc-800 text-zinc-300 mb-2">
                    {tmpl.badge}
                  </span>
                  <h4 className="font-bold text-xs text-zinc-100 group-hover:text-indigo-400 transition-colors mb-1">
                    {tmpl.title}
                  </h4>
                  <p className="text-[11px] text-zinc-400 leading-relaxed mb-3">
                    {tmpl.desc}
                  </p>
                </div>
                <button
                  onClick={() => handleUseTemplate(tmpl)}
                  disabled={isCreating}
                  className="w-full py-1.5 px-3 rounded-lg text-xs font-semibold bg-zinc-800 hover:bg-indigo-600 text-zinc-200 hover:text-white transition-all flex items-center justify-center gap-1"
                >
                  <span>Usar modelo</span>
                  <ArrowRight className="w-3 h-3" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ═══ ESTADO DE CARREGAMENTO / ERRO ═══ */}
      {isLoading && (
        <div className="py-20 text-center text-zinc-500 text-sm">
          Carregando fluxos do seu workspace...
        </div>
      )}

      {error && (
        <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-800/60 text-rose-300 text-sm mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <p className="font-medium text-rose-200">
              {(error as Error).message.toLowerCase().includes('unauthorized') || (error as Error).message.includes('401')
                ? 'Sua sessão expirou ou você não está autenticado.'
                : `Erro ao carregar fluxos: ${(error as Error).message}`}
            </p>
            {((error as Error).message.toLowerCase().includes('unauthorized') || (error as Error).message.includes('401')) && (
              <p className="text-xs text-rose-400 mt-0.5">
                Faça login novamente para acessar os fluxos de conversa e automações do workspace.
              </p>
            )}
          </div>
          {((error as Error).message.toLowerCase().includes('unauthorized') || (error as Error).message.includes('401')) && (
            <a
              href={`/saas/login?next=${encodeURIComponent(window.location.pathname + window.location.search)}`}
              className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-rose-600 hover:bg-rose-500 text-white transition-all shrink-0 shadow-sm"
            >
              <LogIn className="w-3.5 h-3.5" />
              <span>Entrar novamente</span>
            </a>
          )}
        </div>
      )}

      {/* ═══ LISTAGEM MODERNA DOS FLUXOS (PADRÃO CHATBOTX) ═══ */}
      {!isLoading && blueprints.length > 0 && (
        <div className="grid grid-cols-1 gap-3">
          {filteredBlueprints.length === 0 ? (
            <div className="py-12 text-center text-zinc-500 text-sm bg-zinc-900/30 border border-zinc-800/50 rounded-2xl">
              Nenhum fluxo encontrado com o termo "{searchQuery}".
            </div>
          ) : (
            filteredBlueprints.map((bp) => {
              const isPublished = bp.id === publishedId;
              const formattedDate = bp.updated_at
                ? new Date(bp.updated_at).toLocaleDateString('pt-BR', {
                    day: '2-digit',
                    month: 'short',
                    hour: '2-digit',
                    minute: '2-digit',
                  })
                : 'Recentemente';

              return (
                <div
                  key={bp.id}
                  className="group relative flex flex-col sm:flex-row sm:items-center justify-between p-4 sm:p-5 rounded-2xl bg-zinc-900/60 hover:bg-zinc-900/90 border border-zinc-800/80 hover:border-zinc-700 transition-all shadow-sm gap-4"
                >
                  {/* Informações Principais do Fluxo */}
                  <div className="flex items-center gap-3.5 min-w-0">
                    <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 shrink-0">
                      <Workflow className="w-5 h-5" />
                    </div>

                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <Link
                          to={`/flows/${bp.id}`}
                          className="font-semibold text-sm sm:text-base text-zinc-100 hover:text-indigo-400 transition-colors truncate"
                        >
                          {bp.title}
                        </Link>
                        {isPublished ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 shrink-0">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                            Publicado no WhatsApp
                          </span>
                        ) : (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-zinc-800 text-zinc-400 shrink-0">
                            Rascunho
                          </span>
                        )}
                      </div>

                      <div className="flex items-center gap-3 text-xs text-zinc-300 mt-1">
                        <span>slug: <code className="text-zinc-200">{bp.slug}</code></span>
                        <span>•</span>
                        <span className="flex items-center gap-1 text-zinc-300">
                          <Clock className="w-3 h-3 text-zinc-400" />
                          Atualizado em {formattedDate}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Ações Rápidas */}
                  <div className="flex items-center gap-2 self-end sm:self-center shrink-0">
                    <Link
                      to={`/flows/${bp.id}`}
                      className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-semibold bg-zinc-800/80 hover:bg-indigo-600 hover:text-white text-zinc-200 transition-all border border-zinc-700/60"
                    >
                      <span>Abrir Construtor</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </Link>

                    {/* Menu de Opções */}
                    <div className="relative">
                      <button
                        onClick={() => setActiveMenuId(activeMenuId === bp.id ? null : bp.id)}
                        className="p-1.5 rounded-lg text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition-colors"
                      >
                        <MoreVertical className="w-4 h-4" />
                      </button>

                      {activeMenuId === bp.id && (
                        <>
                          <div
                            className="fixed inset-0 z-20"
                            onClick={() => setActiveMenuId(null)}
                          />
                          <div className="absolute right-0 top-full mt-1 w-44 bg-zinc-900 border border-zinc-800 rounded-xl shadow-2xl py-1.5 z-30 text-xs">
                            <button
                              onClick={() => {
                                setActiveMenuId(null);
                                window.open(`/api/flows/blueprints/${bp.id}/export`, '_blank');
                              }}
                              className="w-full text-left px-3 py-2 text-zinc-300 hover:bg-zinc-800 hover:text-white flex items-center gap-2"
                            >
                              <Download className="w-3.5 h-3.5" />
                              Exportar JSON
                            </button>
                            <button
                              onClick={async () => {
                                setActiveMenuId(null);
                                if (confirm(`Deseja excluir o fluxo "${bp.title}"?`)) {
                                  await blueprintsApi.delete(bp.id);
                                  qc.invalidateQueries({ queryKey: ['blueprints'] });
                                  toast.success('Fluxo excluído.');
                                }
                              }}
                              className="w-full text-left px-3 py-2 text-rose-400 hover:bg-rose-950/50 flex items-center gap-2"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                              Excluir Fluxo
                            </button>
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      )}

      {/* ═══ EMPTY STATE COM MODELOS PRONTOS (QUANDO 0 FLUXOS) ═══ */}
      {!isLoading && blueprints.length === 0 && (
        <div className="mt-4">
          <div className="p-8 sm:p-10 rounded-3xl bg-zinc-900/40 border border-zinc-800/80 text-center mb-8 relative overflow-hidden">
            <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 mb-4 shadow-inner">
              <Sparkles className="w-7 h-7" />
            </div>
            <h2 className="text-xl font-bold text-white mb-2">Crie seu primeiro fluxo de WhatsApp</h2>
            <p className="text-sm text-zinc-400 max-w-lg mx-auto mb-6">
              Automações visuais permitem captar clientes, tirar dúvidas com inteligência artificial e fechar vendas no piloto automático.
            </p>
            <button
              onClick={() => {
                setNewFlowTitle('');
                setIsModalOpen(true);
              }}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs sm:text-sm font-semibold bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white shadow-lg shadow-indigo-600/25 active:scale-[0.98] transition-all"
            >
              <Plus className="w-4 h-4" />
              <span>Criar Fluxo em Branco</span>
            </button>
          </div>

          {/* Modelos Recomendados */}
          <div>
            <div className="flex items-center gap-2 mb-4">
              <Layers className="w-4 h-4 text-indigo-400" />
              <h3 className="text-sm font-bold uppercase tracking-wider text-zinc-300">
                Ou comece com um modelo profissional pronto
              </h3>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {STARTER_TEMPLATES.map((tmpl) => (
                <div
                  key={tmpl.id}
                  className="p-5 rounded-2xl bg-zinc-900/60 border border-zinc-800/80 hover:border-zinc-700 flex flex-col justify-between transition-all group"
                >
                  <div>
                    <span className="inline-block px-2 py-0.5 rounded-full text-[10px] font-bold bg-zinc-800 text-zinc-300 mb-3">
                      {tmpl.badge}
                    </span>
                    <h4 className="font-bold text-sm text-zinc-100 group-hover:text-indigo-400 transition-colors mb-1.5">
                      {tmpl.title}
                    </h4>
                    <p className="text-xs text-zinc-400 leading-relaxed mb-4">
                      {tmpl.desc}
                    </p>
                  </div>

                  <button
                    onClick={() => handleUseTemplate(tmpl)}
                    disabled={isCreating}
                    className="w-full py-2 px-3 rounded-xl text-xs font-semibold bg-zinc-800 hover:bg-indigo-600 text-zinc-200 hover:text-white transition-all flex items-center justify-center gap-1.5"
                  >
                    <span>Usar este modelo</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ═══ MODAL MODERNO DE CRIAÇÃO DE FLUXO ═══ */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-150">
          <div className="w-full max-w-md bg-zinc-900 border border-zinc-800 rounded-2xl p-6 shadow-2xl relative">
            <button
              onClick={() => setIsModalOpen(false)}
              className="absolute right-4 top-4 text-zinc-400 hover:text-white"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                <Workflow className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-bold text-base text-white">Criar Novo Fluxo</h3>
                <p className="text-xs text-zinc-400">Dê um nome para o seu funil de atendimento</p>
              </div>
            </div>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (newFlowTitle.trim()) {
                  createBlueprint({
                    title: newFlowTitle.trim(),
                    integration: 'whatsapp',
                    event: 'message',
                  });
                  setIsModalOpen(false);
                }
              }}
              className="space-y-4"
            >
              <div>
                <label className="block text-xs font-semibold text-zinc-300 uppercase tracking-wider mb-1.5">
                  Nome do Fluxo
                </label>
                <input
                  type="text"
                  autoFocus
                  required
                  value={newFlowTitle}
                  onChange={(e) => setNewFlowTitle(e.target.value)}
                  placeholder="ex: Funil de Boas-Vindas & Vendas"
                  className="w-full px-3.5 py-2.5 bg-zinc-950 border border-zinc-800 rounded-xl text-zinc-100 text-sm focus:outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 transition-all placeholder:text-zinc-500"
                />
              </div>

              <div className="flex justify-end gap-2.5 pt-2">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-zinc-400 hover:text-white hover:bg-zinc-800 transition-all"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={!newFlowTitle.trim() || isCreating}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white transition-all shadow-md shadow-indigo-600/20 disabled:opacity-50"
                >
                  {isCreating ? 'Criando...' : 'Criar e Abrir Construtor'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
