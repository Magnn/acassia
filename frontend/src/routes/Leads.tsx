import { useEffect, useMemo, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  MessageSquare,
  User,
  Send,
  Search,
  Bot,
  Clock,
  PauseCircle,
  PlayCircle,
  LayoutList,
  ChevronRight,
  MoreVertical,
  Rows3,
  StretchHorizontal,
  Flame,
  Snowflake,
} from 'lucide-react';
import { inboxApi } from '../api/inbox';
import { composeApi } from '../api/compose';
import { toast } from '../lib/toast';
import ScoreBadge from '../components/ScoreBadge';
import LeadContextPanel from '../components/LeadContextPanel';
import ComposeToolbar from '../components/ComposeToolbar';
import QuickReplyManager from '../components/QuickReplyManager';

type ViewMode = 'chat' | 'table';
type ScoreFilter = null | 'hot' | 'warm' | 'cold';
type SpiritualFilter = null | 'amor' | 'dinheiro' | 'saude' | 'carreira' | 'familia' | 'espiritual' | 'decisao' | 'luto';
type Density = 'comfy' | 'compact';

const SPIRITUAL_EMOJI: Record<string, string> = {
  amor: '❤️', dinheiro: '💰', saude: '🌿', carreira: '💼',
  familia: '🏠', espiritual: '🙏', decisao: '🔀', luto: '🕊️',
};

const DENSITY_KEY = 'acassia.inbox.density';

function ScoreChip({
  label, Icon, color, active, onClick,
}: {
  label: string;
  Icon: typeof Flame;
  color: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1 text-[10px] font-black uppercase tracking-widest px-2.5 py-1 rounded-lg border transition-all ${
        active
          ? 'bg-accent-amethyst text-white border-accent-amethyst'
          : 'bg-bg-primary/50 border-border/50 text-secondary hover:text-primary'
      }`}
    >
      <Icon className={`w-3 h-3 ${active ? 'text-white' : color}`} />
      {label}
    </button>
  );
}

function formatRelativeTime(iso: string | null | undefined): string {
  if (!iso) return '';
  const t = new Date(iso).getTime();
  if (!t) return '';
  const diff = Date.now() - t;
  const min = Math.floor(diff / 60000);
  if (min < 1) return 'agora';
  if (min < 60) return `${min}min`;
  const h = Math.floor(min / 60);
  if (h < 24) return `${h}h`;
  const d = Math.floor(h / 24);
  if (d === 1) return 'ontem';
  if (d < 30) return `${d}d`;
  return '+30d';
}

export default function Leads() {
  const [viewMode, setViewMode] = useState<ViewMode>('chat');
  const [filtro, setFiltro] = useState('todos');
  const [scoreFilter, setScoreFilter] = useState<ScoreFilter>(null);
  const [spiritualFilter, setSpiritualFilter] = useState<SpiritualFilter>(null);
  const [search, setSearch] = useState('');
  const [selectedLeadId, setSelectedLeadId] = useState<number | null>(null);
  const [draft, setDraft] = useState('');
  const [density, setDensity] = useState<Density>(() => {
    const saved = localStorage.getItem(DENSITY_KEY);
    return saved === 'compact' ? 'compact' : 'comfy';
  });
  const [showQuickReplyManager, setShowQuickReplyManager] = useState(false);
  const queryClient = useQueryClient();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);
  const composeRef = useRef<HTMLTextAreaElement>(null);

  const { data: quickReplies } = useQuery({
    queryKey: ['quick-replies'],
    queryFn: composeApi.list,
  });

  useEffect(() => {
    localStorage.setItem(DENSITY_KEY, density);
  }, [density]);

  const { data: leadsData, isLoading: isLoadingLeads } = useQuery({
    queryKey: ['leads-list', filtro, scoreFilter, spiritualFilter],
    queryFn: () => inboxApi.getLeads({
      filtro,
      score_band: scoreFilter || undefined,
      spiritual_category: spiritualFilter || undefined,
      sort: 'score',
      limit: 200,
    }),
    refetchInterval: 10000,
  });

  const { data: conversationData } = useQuery({
    queryKey: ['leads-conversation', selectedLeadId],
    queryFn: () => inboxApi.getConversation(selectedLeadId!),
    enabled: selectedLeadId !== null,
    refetchInterval: 5000,
  });

  const takeoverMutation = useMutation({
    mutationFn: inboxApi.toggleTakeover,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads-conversation', selectedLeadId] });
      queryClient.invalidateQueries({ queryKey: ['leads-list'] });
    },
    onError: (e) => toast.error((e as Error).message),
  });

  const sendMutation = useMutation({
    mutationFn: ({ leadId, text }: { leadId: number; text: string }) =>
      inboxApi.sendMessage(leadId, text),
    onSuccess: () => {
      setDraft('');
      queryClient.invalidateQueries({ queryKey: ['leads-conversation', selectedLeadId] });
      queryClient.invalidateQueries({ queryKey: ['leads-list'] });
    },
    onError: (e) => toast.error(`Falha ao enviar: ${(e as Error).message}`),
  });

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [conversationData?.messages]);

  const leads = useMemo(() =>
    (leadsData?.items || []).filter(l =>
      l.nome?.toLowerCase().includes(search.toLowerCase()) ||
      l.telefone?.includes(search),
    ),
    [leadsData?.items, search],
  );

  // Atalhos de teclado: j/k navegar, / busca, Esc desselecionar
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const target = e.target as HTMLElement | null;
      const inField = !!target?.closest('input, textarea, [contenteditable]');
      if (e.key === '/' && !inField) {
        e.preventDefault();
        searchRef.current?.focus();
        return;
      }
      if (inField) return;
      if (e.key === 'Escape') {
        setSelectedLeadId(null);
        return;
      }
      if (e.key === 'j' || e.key === 'k') {
        if (leads.length === 0) return;
        const currentIdx = leads.findIndex((l) => l.id === selectedLeadId);
        let next = currentIdx;
        if (e.key === 'j') next = currentIdx < 0 ? 0 : Math.min(leads.length - 1, currentIdx + 1);
        else next = currentIdx <= 0 ? 0 : currentIdx - 1;
        setSelectedLeadId(leads[next].id);
        return;
      }
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [leads, selectedLeadId]);

  // Atalhos 1-9 para Quick Replies (somente quando textarea está focada)
  useEffect(() => {
    const items = quickReplies?.quick_replies ?? [];
    function onCompKey(e: KeyboardEvent) {
      const target = e.target as HTMLElement | null;
      if (target !== composeRef.current) return;
      if (!e.altKey) return;
      if (!/^[1-9]$/.test(e.key)) return;
      const num = Number(e.key);
      const tpl = items.find((q) => q.shortcut_number === num);
      if (!tpl || !selectedLeadId) return;
      e.preventDefault();
      composeApi.render(tpl.id, selectedLeadId)
        .then((res) => insertAtCursor(res.text))
        .catch(() => {});
    }
    window.addEventListener('keydown', onCompKey);
    return () => window.removeEventListener('keydown', onCompKey);
  }, [quickReplies, selectedLeadId]);

  function insertAtCursor(text: string) {
    const el = composeRef.current;
    if (!el) {
      setDraft((d) => (d ? `${d}\n${text}` : text));
      return;
    }
    const start = el.selectionStart ?? draft.length;
    const end = el.selectionEnd ?? draft.length;
    const next = draft.slice(0, start) + text + draft.slice(end);
    setDraft(next);
    requestAnimationFrame(() => {
      el.focus();
      const pos = start + text.length;
      el.setSelectionRange(pos, pos);
    });
  }
  
  const selectedLead = conversationData?.lead;
  const messages = conversationData?.messages || [];

  const handleSend = () => {
    const text = draft.trim();
    if (!text || selectedLeadId == null) return;
    if (!selectedLead?.bot_pausado) {
      if (!confirm('O bot ainda está ativo. Continuar pode atrapalhar a automação. Confirmar envio?')) return;
    }
    sendMutation.mutate({ leadId: selectedLeadId, text });
  };

  return (
    <div className="flex h-full w-full bg-bg-primary text-primary overflow-hidden">
      {/* Sidebar de Leads - Sempre Visível ou Toggleable */}
      <div className={`flex-shrink-0 border-r border-border bg-bg-sidebar transition-all duration-300 ${viewMode === 'table' ? 'w-0 opacity-0 overflow-hidden' : 'w-[380px]'}`}>
        <div className="p-6 border-b border-border bg-bg-sidebar/50">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-black tracking-tight">Conversas</h2>
            <button 
              onClick={() => setViewMode('table')}
              className="p-2 rounded-xl hover:bg-bg-primary text-secondary hover:text-accent-amethyst transition-all"
              title="Mudar para visualização em Lista"
            >
              <LayoutList className="w-5 h-5" />
            </button>
          </div>

          <div className="space-y-4">
            {/* Search Bar Unificada */}
            <div className="relative group">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-secondary group-focus-within:text-accent-amethyst transition-colors" />
              <input
                ref={searchRef}
                type="text"
                placeholder="Buscar lead… (/)"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full bg-bg-primary/50 border border-border/50 rounded-2xl pl-11 pr-4 py-2.5 text-xs outline-none focus:border-accent-amethyst focus:bg-bg-primary transition-all shadow-inner"
              />
            </div>

            {/* Filtros Status */}
            <div className="flex bg-bg-primary/50 p-1 rounded-xl border border-border/50 overflow-x-auto scrollbar-hide">
              {['todos', 'ativas', 'pausadas'].map((f) => (
                <button
                  key={f}
                  onClick={() => setFiltro(f)}
                  className={`flex-1 text-[10px] font-black uppercase tracking-widest py-1.5 px-3 rounded-lg capitalize transition-all whitespace-nowrap ${
                    filtro === f ? 'bg-accent-amethyst text-white shadow-lg' : 'text-secondary hover:text-primary hover:bg-bg-surface/50'
                  }`}
                >
                  {f}
                </button>
              ))}
            </div>

            {/* Filtros Score + Densidade */}
            <div className="flex items-center gap-1.5 flex-wrap">
              <ScoreChip
                label="Hot"
                Icon={Flame}
                color="text-rose-400"
                active={scoreFilter === 'hot'}
                onClick={() => setScoreFilter(scoreFilter === 'hot' ? null : 'hot')}
              />
              <ScoreChip
                label="Warm"
                Icon={Flame}
                color="text-amber-400"
                active={scoreFilter === 'warm'}
                onClick={() => setScoreFilter(scoreFilter === 'warm' ? null : 'warm')}
              />
              <ScoreChip
                label="Cold"
                Icon={Snowflake}
                color="text-sky-400"
                active={scoreFilter === 'cold'}
                onClick={() => setScoreFilter(scoreFilter === 'cold' ? null : 'cold')}
              />
              <button
                onClick={() => setDensity(density === 'comfy' ? 'compact' : 'comfy')}
                title={density === 'comfy' ? 'Densidade compacta' : 'Densidade confortável'}
                className="ml-auto p-1.5 rounded-lg border border-border/50 text-secondary hover:text-primary hover:bg-bg-surface/50"
              >
                {density === 'comfy' ? (
                  <Rows3 className="w-3.5 h-3.5" />
                ) : (
                  <StretchHorizontal className="w-3.5 h-3.5" />
                )}
              </button>
            </div>

            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="text-[9px] font-black uppercase tracking-widest text-secondary mr-0.5">Tema:</span>
              {(['amor', 'dinheiro', 'familia', 'carreira', 'espiritual', 'decisao', 'saude', 'luto'] as const).map((c) => (
                <button
                  key={c}
                  onClick={() => setSpiritualFilter(spiritualFilter === c ? null : c)}
                  title={c}
                  className={`text-[10px] px-2 py-1 rounded-lg border transition-all flex items-center gap-1 ${
                    spiritualFilter === c
                      ? 'bg-accent-amethyst text-white border-accent-amethyst'
                      : 'bg-bg-primary/50 border-border/50 text-secondary hover:text-primary'
                  }`}
                >
                  <span>{SPIRITUAL_EMOJI[c]}</span>
                  <span className="font-bold capitalize">{c}</span>
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto space-y-1 p-3 scrollbar-hide">
          {isLoadingLeads ? (
             <div className="p-8 text-center text-[10px] font-black uppercase tracking-widest text-secondary animate-pulse">Sincronizando Leads...</div>
          ) : leads.length === 0 ? (
            <div className="p-12 text-center opacity-40">
               <MessageSquare className="w-8 h-8 mx-auto mb-3" />
               <p className="text-[10px] font-black uppercase tracking-widest">Nenhuma conversa encontrada</p>
            </div>
          ) : (
            leads.map((l) => {
              const isCompact = density === 'compact';
              const isInbound = l.ultima_remetente === 'lead';
              const previewIcon = isInbound ? '📩' : '📤';
              return (
                <div
                  key={l.id}
                  onClick={() => setSelectedLeadId(l.id)}
                  className={`${isCompact ? 'p-2.5' : 'p-4'} rounded-2xl cursor-pointer transition-all border border-transparent relative group mb-1 ${
                    selectedLeadId === l.id ? 'bg-bg-surface border-border shadow-md' : 'hover:bg-bg-surface/40'
                  }`}
                >
                  {selectedLeadId === l.id && (
                    <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-accent-amethyst rounded-r-full shadow-[0_0_15px_rgba(var(--accent-amethyst-rgb),0.5)]" />
                  )}
                  <div className="flex justify-between items-start gap-2">
                    <div className="flex items-center gap-2 min-w-0 flex-1">
                      {l.score_band && l.score_band !== 'cold' && (
                        <ScoreBadge band={l.score_band} value={l.score_value} />
                      )}
                      <div className={`font-black truncate tracking-tight group-hover:text-accent-amethyst transition-colors ${isCompact ? 'text-xs' : 'text-sm'}`}>
                        {l.nome || l.telefone}
                      </div>
                    </div>
                    {l.ultima_em && (
                      <div className="text-[9px] text-secondary font-black tabular-nums flex-shrink-0">
                        {formatRelativeTime(l.ultima_em)}
                      </div>
                    )}
                  </div>
                  {!isCompact && (
                    <div className="text-[11px] text-secondary/80 font-medium line-clamp-1 mt-1.5">
                      <span className="opacity-60 mr-1">{previewIcon}</span>
                      {l.ultima_msg || '(Sem mensagens)'}
                    </div>
                  )}
                  {!isCompact && (
                    <div className="flex gap-1.5 mt-2 flex-wrap">
                      {l.spiritual_category && (
                        <span
                          className={`text-[8px] uppercase tracking-widest px-1.5 py-0.5 rounded-md font-black border flex items-center gap-1 ${
                            l.spiritual_urgency === 'high'
                              ? 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                              : 'bg-accent-amethyst/10 text-accent-amethyst border-accent-amethyst/30'
                          }`}
                          title={`Tema: ${l.spiritual_category}${l.spiritual_urgency ? ` · urgência ${l.spiritual_urgency}` : ''}`}
                        >
                          {SPIRITUAL_EMOJI[l.spiritual_category] || '✦'}
                          {l.spiritual_category}
                        </span>
                      )}
                      {l.bot_pausado && (
                        <span className="bg-amber-500/10 text-amber-500 text-[8px] uppercase tracking-widest px-1.5 py-0.5 rounded-md font-black border border-amber-500/20">
                          Pausado
                        </span>
                      )}
                      {l.convertido && (
                        <span className="bg-emerald-500/10 text-emerald-500 text-[8px] uppercase tracking-widest px-1.5 py-0.5 rounded-md font-black border border-emerald-500/20">
                          Venda
                        </span>
                      )}
                      {(l.tags || []).slice(0, 2).map((tag) => (
                        <span
                          key={tag}
                          className="bg-bg-primary text-secondary text-[8px] uppercase tracking-widest px-1.5 py-0.5 rounded-md font-black border border-border/50"
                        >
                          #{tag}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Área Principal (Chat ou Tabela) */}
      <div className="flex-1 flex flex-col min-w-0 bg-bg-primary relative overflow-hidden">
        {viewMode === 'table' ? (
          <div className="flex-1 flex flex-col p-10 max-w-7xl mx-auto w-full animate-in fade-in duration-500">
            <div className="flex items-center justify-between mb-8">
              <div>
                <h2 className="text-3xl font-black tracking-tight">Gestão de Leads</h2>
                <p className="text-sm text-secondary font-medium mt-1">Visão completa da base de contatos.</p>
              </div>
              <div className="flex items-center gap-3">
                 <div className="relative group w-64">
                    <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-secondary" />
                    <input 
                      type="text"
                      placeholder="Pesquisar..."
                      value={search}
                      onChange={(e) => setSearch(e.target.value)}
                      className="w-full bg-bg-surface border border-border rounded-2xl pl-11 pr-4 py-2.5 text-xs outline-none focus:border-accent-amethyst transition-all shadow-sm"
                    />
                 </div>
                 <button 
                  onClick={() => setViewMode('chat')}
                  className="flex items-center gap-2 px-6 py-2.5 bg-accent-amethyst text-white rounded-2xl text-xs font-black uppercase tracking-widest shadow-lg shadow-accent-amethyst/20 hover:scale-105 active:scale-95 transition-all"
                >
                  <MessageSquare className="w-4 h-4" />
                  Abrir Conversas
                </button>
              </div>
            </div>

            <div className="bg-bg-surface border border-border rounded-[32px] flex-1 overflow-hidden shadow-premium flex flex-col">
               <div className="p-4 border-b border-border bg-bg-sidebar/20 flex items-center justify-between">
                  <div className="flex items-center gap-4">
                     {['todos', 'ativas', 'pausadas', 'convertidas'].map(f => (
                       <button 
                        key={f}
                        onClick={() => setFiltro(f)}
                        className={`text-[10px] font-black uppercase tracking-widest px-4 py-2 rounded-xl transition-all ${filtro === f ? 'bg-bg-primary text-accent-amethyst border border-accent-amethyst/30' : 'text-secondary hover:text-primary'}`}
                       >
                         {f}
                       </button>
                     ))}
                  </div>
                  <div className="text-[10px] font-black uppercase tracking-widest text-secondary/50">{leads.length} resultados</div>
               </div>
               
               <div className="flex-1 overflow-auto scrollbar-hide">
                  <table className="w-full text-left border-separate border-spacing-0">
                    <thead className="bg-bg-primary/50 sticky top-0 z-10 backdrop-blur-md">
                       <tr>
                         <th className="py-5 px-8 text-[9px] font-black uppercase tracking-[0.2em] text-secondary border-b border-border">Lead</th>
                         <th className="py-5 px-8 text-[9px] font-black uppercase tracking-[0.2em] text-secondary border-b border-border">Status</th>
                         <th className="py-5 px-8 text-[9px] font-black uppercase tracking-[0.2em] text-secondary border-b border-border">Fluxo</th>
                         <th className="py-5 px-8 text-[9px] font-black uppercase tracking-[0.2em] text-secondary border-b border-border">Última Msg</th>
                         <th className="py-5 px-8 text-[9px] font-black uppercase tracking-[0.2em] text-secondary border-b border-border text-right">Ação</th>
                       </tr>
                    </thead>
                    <tbody className="divide-y divide-border/30">
                       {leads.map(l => (
                         <tr key={l.id} className="group hover:bg-bg-primary/40 transition-all">
                            <td className="py-5 px-8">
                               <div className="flex items-center gap-4">
                                  <div className="w-10 h-10 rounded-2xl bg-bg-primary border border-border flex items-center justify-center font-black text-accent-amethyst shadow-sm">
                                     <User className="w-5 h-5" />
                                  </div>
                                  <div>
                                     <div className="font-black text-sm tracking-tight">{l.nome || '(Sem Nome)'}</div>
                                     <div className="text-[10px] text-secondary font-black opacity-60">{l.telefone}</div>
                                  </div>
                               </div>
                            </td>
                            <td className="py-5 px-8">
                               <div className="flex gap-2 flex-wrap">
                                  {l.score_band && (
                                    <ScoreBadge band={l.score_band} value={l.score_value} />
                                  )}
                                  {l.bot_pausado ? (
                                    <span className="bg-amber-500/10 text-amber-500 text-[8px] uppercase tracking-widest px-2 py-1 rounded-lg font-black border border-amber-500/20">Pausado</span>
                                  ) : (
                                    <span className="bg-sky-500/10 text-sky-500 text-[8px] uppercase tracking-widest px-2 py-1 rounded-lg font-black border border-sky-500/20">Ativo</span>
                                  )}
                                  {l.convertido && (
                                    <span className="bg-emerald-500/10 text-emerald-500 text-[8px] uppercase tracking-widest px-2 py-1 rounded-lg font-black border border-emerald-500/20">Venda</span>
                                  )}
                               </div>
                            </td>
                            <td className="py-5 px-8">
                               <div className="flex items-center gap-2">
                                  <div className="p-1.5 rounded-lg bg-bg-primary border border-border">
                                     <Bot className="w-3 h-3 text-accent-amethyst" />
                                  </div>
                                  <span className="text-xs font-bold text-primary">{l.node_atual || 'Início'}</span>
                               </div>
                            </td>
                            <td className="py-5 px-8">
                               <div className="max-w-[200px] truncate text-xs text-secondary font-medium">{l.ultima_msg || '---'}</div>
                               <div className="text-[9px] font-black text-secondary/40 mt-1">{l.ultima_em ? new Date(l.ultima_em).toLocaleDateString() : ''}</div>
                            </td>
                            <td className="py-5 px-8 text-right">
                               <div className="flex items-center justify-end gap-2">
                                 <button 
                                  onClick={() => takeoverMutation.mutate(l.id)}
                                  className={`p-2 rounded-xl border transition-all ${
                                    l.bot_pausado 
                                      ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-500 hover:bg-emerald-500 hover:text-white' 
                                      : 'bg-amber-500/10 border-amber-500/20 text-amber-500 hover:bg-amber-500 hover:text-white'
                                  }`}
                                  title={l.bot_pausado ? 'Liberar Robô' : 'Pausar Robô'}
                                 >
                                   {l.bot_pausado ? <PlayCircle className="w-4 h-4" /> : <PauseCircle className="w-4 h-4" />}
                                 </button>
                                 <button 
                                  onClick={() => {
                                    setSelectedLeadId(l.id);
                                    setViewMode('chat');
                                  }}
                                  className="inline-flex items-center gap-2 px-4 py-2 bg-bg-primary border border-border hover:border-accent-amethyst/30 hover:text-accent-amethyst rounded-xl text-[9px] font-black uppercase tracking-widest transition-all"
                                 >
                                   Chat
                                   <ChevronRight className="w-3 h-3" />
                                 </button>
                               </div>
                            </td>
                         </tr>
                       ))}
                    </tbody>
                  </table>
               </div>
            </div>
          </div>
        ) : (
          /* Visualização de Chat Unificada */
          <div className="flex-1 flex flex-col h-full bg-bg-primary animate-in slide-in-from-right-4 duration-300">
            {!selectedLeadId ? (
              <div className="flex-1 flex flex-col items-center justify-center text-secondary bg-bg-primary/30 backdrop-blur-sm">
                <div className="w-24 h-24 rounded-[40px] bg-bg-surface border border-border shadow-premium flex items-center justify-center mb-8 group transition-all hover:scale-110">
                   <MessageSquare className="w-10 h-10 opacity-20 text-accent-amethyst group-hover:opacity-100 transition-opacity" />
                </div>
                <h3 className="text-xl font-black tracking-tight text-primary mb-2">Central de Atendimento</h3>
                <p className="text-xs font-bold uppercase tracking-widest opacity-40">Selecione uma conversa para começar</p>
                <div className="mt-4 flex items-center gap-3 text-[9px] font-black uppercase tracking-widest opacity-40">
                  <span><kbd className="px-1.5 py-0.5 rounded bg-bg-surface border border-border">/</kbd> buscar</span>
                  <span><kbd className="px-1.5 py-0.5 rounded bg-bg-surface border border-border">j/k</kbd> navegar</span>
                  <span><kbd className="px-1.5 py-0.5 rounded bg-bg-surface border border-border">Esc</kbd> sair</span>
                </div>
                
                <button 
                  onClick={() => setViewMode('table')}
                  className="mt-8 flex items-center gap-2 text-[10px] font-black uppercase tracking-widest text-accent-amethyst hover:underline"
                >
                  <LayoutList className="w-3.5 h-3.5" />
                  Ver todos os contatos em lista
                </button>
              </div>
            ) : (
              <>
                {/* Header Unificado */}
                <div className="h-[80px] px-8 bg-bg-header/50 backdrop-blur-md border-b border-border flex items-center justify-between z-10 flex-shrink-0">
                   <div className="flex items-center gap-4">
                      <div className="w-12 h-12 rounded-2xl bg-bg-primary border border-border text-accent-amethyst flex items-center justify-center font-bold shadow-sm group cursor-pointer hover:rotate-3 transition-transform">
                        <User className="w-6 h-6" />
                      </div>
                      <div className="min-w-0">
                         <h3 className="font-black text-primary leading-tight text-xl tracking-tight truncate">{selectedLead?.nome || selectedLead?.telefone}</h3>
                         <div className="flex items-center gap-2 text-[10px] text-secondary font-black uppercase tracking-widest opacity-70">
                            <span>{selectedLead?.telefone}</span>
                            <span className="w-1 h-1 rounded-full bg-border" />
                            <span className="text-accent-amethyst">{selectedLead?.node_atual}</span>
                         </div>
                      </div>
                   </div>
                   <div className="flex items-center gap-3">
                      <button
                        onClick={() => takeoverMutation.mutate(selectedLeadId)}
                        disabled={takeoverMutation.isPending}
                        className={`flex items-center gap-2.5 px-6 py-2.5 rounded-2xl text-[10px] font-black uppercase tracking-widest transition-all shadow-lg border ${
                          selectedLead?.bot_pausado
                            ? 'bg-emerald-500 text-white border-emerald-400 shadow-emerald-500/20'
                            : 'bg-amber-500 text-white border-amber-400 shadow-amber-500/20'
                        }`}
                      >
                        {selectedLead?.bot_pausado ? <PlayCircle className="w-4 h-4" /> : <PauseCircle className="w-4 h-4" />}
                        {selectedLead?.bot_pausado ? 'Liberar Robô' : 'Assumir Controle'}
                      </button>
                      <button className="p-2.5 rounded-2xl border border-border bg-bg-surface hover:bg-bg-primary text-secondary transition-all">
                         <MoreVertical className="w-5 h-5" />
                      </button>
                   </div>
                </div>

                {/* Mensagens */}
                <div className="flex-1 overflow-y-auto p-8 space-y-6 scrollbar-hide bg-gradient-to-b from-transparent to-bg-primary/30">
                  {messages.map((m) => {
                    const isUser = m.origem === 'lead';
                    const isSystem = m.origem === 'system';
                    
                    if (isSystem) {
                      return (
                        <div key={m.id} className="flex justify-center py-2">
                          <div className="bg-bg-surface border border-border text-primary text-[11px] font-bold italic px-4 py-2 rounded-2xl shadow-sm opacity-60">
                            {m.texto}
                          </div>
                        </div>
                      );
                    }

                    return (
                      <div key={m.id} className={`flex ${isUser ? 'justify-start' : 'justify-end'}`}>
                        <div className={`flex flex-col max-w-[75%] ${isUser ? 'items-start' : 'items-end'}`}>
                          <div
                            className={`px-5 py-3 text-sm shadow-premium relative transition-all hover:scale-[1.02] ${
                              isUser
                                ? 'bg-bg-surface border border-border text-primary rounded-[28px] rounded-tl-sm'
                                : 'bg-accent-amethyst text-white border border-accent-amethyst/20 rounded-[28px] rounded-tr-sm shadow-accent-amethyst/10'
                            }`}
                          >
                            <div className="whitespace-pre-wrap break-words leading-relaxed font-medium">{m.texto || '(Mídia)'}</div>
                            <div className={`text-[9px] font-black mt-2 flex items-center justify-end gap-1.5 opacity-40`}>
                              {m.timestamp && new Date(m.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                              {!isUser && <Clock className="w-2.5 h-2.5" />}
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                  <div ref={messagesEndRef} />
                </div>

                {/* Input Unificado */}
                <div className="bg-bg-surface/80 backdrop-blur-xl border-t border-border p-6 flex-shrink-0 z-10">
                   <div className="max-w-5xl mx-auto">
                     <div className="relative">
                       <ComposeToolbar
                         leadId={selectedLeadId}
                         onInsert={insertAtCursor}
                         onOpenManager={() => setShowQuickReplyManager(true)}
                       />
                     </div>
                     <div className="flex items-end gap-4">
                       <div className="flex-1 relative group">
                         <textarea
                           ref={composeRef}
                           value={draft}
                           onChange={(e) => setDraft(e.target.value)}
                           onKeyDown={(e) => {
                             if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                               e.preventDefault();
                               handleSend();
                             }
                           }}
                           placeholder={
                             selectedLead?.bot_pausado
                               ? "Sua mensagem manual… (Ctrl+Enter envia · Alt+1-9 templates)"
                               : "Pause o robô para responder manualmente…"
                           }
                           rows={Math.min(6, Math.max(2, draft.split('\n').length))}
                           className="w-full bg-bg-primary/50 border-2 border-border/50 rounded-2xl px-6 py-3 text-sm text-primary outline-none focus:border-accent-amethyst/50 focus:bg-bg-primary transition-all shadow-inner resize-none"
                         />
                         {draft.length > 800 && (
                           <div className={`absolute -top-1 right-4 text-[10px] font-black tabular-nums ${
                             draft.length > 1000 ? 'text-rose-400' : 'text-amber-400'
                           }`}>
                             {draft.length}/1000
                           </div>
                         )}
                       </div>
                       <button
                         onClick={handleSend}
                         disabled={!draft.trim() || sendMutation.isPending}
                         className="w-[56px] h-[56px] bg-accent-amethyst text-white rounded-2xl flex items-center justify-center hover:scale-105 active:scale-95 transition-all shadow-lg shadow-accent-amethyst/20 disabled:opacity-30 disabled:scale-100"
                       >
                          <Send className="w-5 h-5" />
                       </button>
                     </div>
                   </div>
                   
                   <div className="mt-4 flex items-center justify-center gap-6 opacity-60">
                      <button 
                        onClick={() => inboxApi.resumeLastUser(selectedLeadId!).then(() => queryClient.invalidateQueries({ queryKey: ['leads-conversation', selectedLeadId] }))}
                        className="text-[9px] font-black uppercase tracking-widest hover:text-accent-amethyst transition-colors"
                      >
                        ↻ Reprocessar Última
                      </button>
                      <div className="w-1 h-1 rounded-full bg-border" />
                      <button 
                        onClick={() => inboxApi.resendCurrentBlock(selectedLeadId!).then(() => queryClient.invalidateQueries({ queryKey: ['leads-conversation', selectedLeadId] }))}
                        className="text-[9px] font-black uppercase tracking-widest hover:text-accent-amethyst transition-colors"
                      >
                        ⟳ Reenviar Bloco Atual
                      </button>
                   </div>
                </div>
              </>
            )}
          </div>
        )}
      </div>

      {showQuickReplyManager && (
        <QuickReplyManager onClose={() => setShowQuickReplyManager(false)} />
      )}

      {/* 3ª coluna: Contexto do lead — só no chat mode com lead selecionado */}
      {viewMode === 'chat' && selectedLeadId !== null && (
        <div className="hidden lg:block w-[320px] flex-shrink-0 border-l border-border bg-bg-sidebar/30 overflow-y-auto">
          <div className="p-3 border-b border-border bg-bg-sidebar/50">
            <h3 className="text-xs font-black uppercase tracking-widest text-secondary">
              Contexto
            </h3>
          </div>
          <LeadContextPanel leadId={selectedLeadId} />
        </div>
      )}
    </div>
  );
}
