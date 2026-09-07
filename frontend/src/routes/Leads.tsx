import { useEffect, useMemo, useRef, useState, useCallback } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  AlertTriangle,
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
  Mic,
  MicOff,
} from 'lucide-react';
import { inboxApi } from '../api/inbox';
import { composeApi } from '../api/compose';
import { toast } from '../lib/toast';
import ScoreBadge from '../components/ScoreBadge';
import LeadContextPanel from '../components/LeadContextPanel';
import ComposeToolbar from '../components/ComposeToolbar';
import QuickReplyManager from '../components/QuickReplyManager';
import AudioComposeModal from '../components/AudioComposeModal';
import VoiceOnlyCompose from '../components/VoiceOnlyCompose';
import { useInboxRealtime } from '../hooks/useInboxRealtime';
import { useNotificationSound } from '../hooks/useNotificationSound';
import TypingIndicator from '../components/inbox/TypingIndicator';
import UnreadBadge from '../components/inbox/UnreadBadge';
import ScrollToBottom from '../components/inbox/ScrollToBottom';
import ConnectionStatus from '../components/inbox/ConnectionStatus';
import WhatsAppChatView from '../components/inbox/WhatsAppChatView';

type ViewMode = 'chat' | 'table';
type ScoreFilter = null | 'hot' | 'warm' | 'cold';
type IntentFilter = null | 'amor' | 'dinheiro' | 'saude' | 'carreira' | 'familia' | 'consultoria' | 'decisao' | 'luto';
type Density = 'comfy' | 'compact';

const INTENT_EMOJI: Record<string, string> = {
  amor: '❤️', dinheiro: '💰', saude: '🌿', carreira: '💼',
  familia: '🏠', consultoria: '💡', decisao: '🔀', luto: '🕊️',
};

const DENSITY_KEY = 'acassia.inbox.density';
const VOICE_ONLY_KEY = 'acassia.inbox.voice_only';

function DeliveryStatus({ status }: { status: string | null | undefined }) {
  if (!status) return <Clock className="w-2.5 h-2.5" />;
  if (status === 'failed') {
    return <span title="Falhou">⚠</span>;
  }
  if (status === 'read') {
    return <span title="Lida" className="text-sky-400">✓✓</span>;
  }
  if (status === 'delivered') {
    return <span title="Entregue">✓✓</span>;
  }
  // sent
  return <span title="Enviado">✓</span>;
}


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
  const [intentFilter, setIntentFilter] = useState<IntentFilter>(null);
  const [search, setSearch] = useState('');
  const [selectedLeadId, setSelectedLeadId] = useState<number | null>(null);
  const [draft, setDraft] = useState('');
  const [density, setDensity] = useState<Density>(() => {
    const saved = localStorage.getItem(DENSITY_KEY);
    return saved === 'compact' ? 'compact' : 'comfy';
  });
  const [showQuickReplyManager, setShowQuickReplyManager] = useState(false);
  const [showAudioCompose, setShowAudioCompose] = useState(false);
  const [voiceOnlyMode, setVoiceOnlyMode] = useState<boolean>(() => {
    return localStorage.getItem(VOICE_ONLY_KEY) === '1';
  });
  const [showLeadDrawer, setShowLeadDrawer] = useState(true);
  const lastReadMsgIdRef = useRef<number | null>(null);
  const [showScrollBtn, setShowScrollBtn] = useState(false);
  const chatContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    localStorage.setItem(VOICE_ONLY_KEY, voiceOnlyMode ? '1' : '0');
  }, [voiceOnlyMode]);
  const queryClient = useQueryClient();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);
  const composeRef = useRef<HTMLTextAreaElement>(null);

  // ── Real-time SSE ──
  const { play: playNotification } = useNotificationSound();
  const { connected, typingLeadIds, unreadMap, totalUnread } = useInboxRealtime({
    selectedLeadId: selectedLeadId,
    onNewMessage: (evt) => {
      // Tocar som apenas se mensagem é de lead (incoming)
      if (evt.lead_id !== selectedLeadId) {
        playNotification();
      }
    },
  });

  // ── Scroll detection (show/hide scroll-to-bottom button) ──
  const handleChatScroll = useCallback(() => {
    const el = chatContainerRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
    setShowScrollBtn(!atBottom);
  }, []);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    setShowScrollBtn(false);
  }, []);

  const { data: quickReplies } = useQuery({
    queryKey: ['quick-replies'],
    queryFn: composeApi.list,
  });

  useEffect(() => {
    localStorage.setItem(DENSITY_KEY, density);
  }, [density]);

  const { data: leadsData, isLoading: isLoadingLeads } = useQuery({
    queryKey: ['leads-list', filtro, scoreFilter, intentFilter],
    queryFn: () => inboxApi.getLeads({
      filtro,
      score_band: scoreFilter || undefined,
      spiritual_category: intentFilter || undefined,
      sort: 'score',
      limit: 200,
    }),
    refetchInterval: 60_000, // fallback safety-net (SSE handles real-time via invalidation)
  });

  const { data: conversationData } = useQuery({
    queryKey: ['leads-conversation', selectedLeadId],
    queryFn: () => inboxApi.getConversation(selectedLeadId!),
    enabled: selectedLeadId !== null,
    refetchInterval: 30_000, // fallback safety-net (SSE pushes conversation updates)
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

  // Voice-only mode: auto-play TTS de novas msgs do lead via SpeechSynthesis
  useEffect(() => {
    if (!voiceOnlyMode) return;
    const messages = conversationData?.messages || [];
    if (messages.length === 0) return;
    const lastMsg = messages[messages.length - 1];
    if (!lastMsg || lastReadMsgIdRef.current === lastMsg.id) return;
    if (lastMsg.origem !== 'lead') {
      lastReadMsgIdRef.current = lastMsg.id;
      return;
    }
    if (!('speechSynthesis' in window)) return;
    try {
      window.speechSynthesis.cancel();
      const utter = new SpeechSynthesisUtterance(lastMsg.texto || '');
      utter.lang = 'pt-BR';
      utter.rate = 0.95;
      window.speechSynthesis.speak(utter);
      lastReadMsgIdRef.current = lastMsg.id;
    } catch {
      // ignora
    }
  }, [voiceOnlyMode, conversationData?.messages]);

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
            <div className="flex items-center gap-3">
              <h2 className="text-xl font-black tracking-tight">Conversas</h2>
              <ConnectionStatus connected={connected} />
              {totalUnread > 0 && <UnreadBadge count={totalUnread} />}
            </div>
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
              <span className="text-[9px] font-black uppercase tracking-widest text-secondary mr-0.5">Status:</span>
              {[
                { id: 'all', label: 'Todas' },
                { id: 'ativas', label: 'Ativas' },
                { id: 'convertidos', label: 'Convertidos' },
                { id: 'pausadas', label: 'Pausadas' },
              ].map((st) => (
                <button
                  key={st.id}
                  onClick={() => setFiltro(st.id)}
                  className={`text-[10px] px-2.5 py-1 rounded-lg border transition-all font-bold ${
                    filtro === st.id
                      ? 'bg-indigo-600 text-white border-indigo-500 shadow-sm'
                      : 'bg-bg-primary/50 border-border/50 text-secondary hover:text-primary hover:bg-bg-surface'
                  }`}
                >
                  {st.label}
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
              const initials = (l.nome || l.telefone || 'WA').slice(0, 2).toUpperCase();
              const isSelected = selectedLeadId === l.id;
              const unreadCount = unreadMap.get(l.id) || 0;

              return (
                <div
                  key={l.id}
                  onClick={() => setSelectedLeadId(l.id)}
                  className={`${isCompact ? 'p-2' : 'p-3'} rounded-2xl cursor-pointer transition-all border relative group mb-1.5 ${
                    l.is_urgent
                      ? 'border-red-500/60 ring-1 ring-red-500/30 bg-red-500/5'
                      : isSelected
                      ? 'bg-[#2a3942]/70 border-[#00a884]/40 shadow-sm'
                      : 'border-transparent hover:bg-[#202c33]/70'
                  } ${unreadCount > 0 && !l.is_urgent ? 'ring-1 ring-[#00a884]/40' : ''}`}
                >
                  {isSelected && (
                    <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-[#00a884] rounded-r-full shadow-[0_0_12px_rgba(0,168,132,0.6)]" />
                  )}
                  <div className="flex items-start gap-3">
                    <div
                      className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-xs flex-shrink-0 mt-0.5 shadow-sm transition-colors ${
                        isSelected
                          ? 'bg-[#00a884] text-white'
                          : 'bg-[#202c33] border border-[#2a3942] text-[#00a884] group-hover:bg-[#2a3942]'
                      }`}
                    >
                      {initials}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex justify-between items-center gap-1">
                        <div className="flex items-center gap-1.5 min-w-0">
                          {l.score_band && l.score_band !== 'cold' && (
                            <ScoreBadge band={l.score_band} value={l.score_value} />
                          )}
                          <div className={`font-bold truncate text-[#e9edef] group-hover:text-[#00a884] transition-colors ${isCompact ? 'text-xs' : 'text-sm'}`}>
                            {l.nome || l.telefone}
                          </div>
                        </div>
                        <div className="flex items-center gap-1.5 flex-shrink-0">
                          {unreadCount > 0 && (
                            <span className="bg-[#00a884] text-white text-[10px] font-bold px-1.5 py-0.2 rounded-full shadow-sm">
                              {unreadCount}
                            </span>
                          )}
                          {l.ultima_em && (
                            <div className="text-[10px] text-[#8696a0] tabular-nums font-mono">
                              {formatRelativeTime(l.ultima_em)}
                            </div>
                          )}
                        </div>
                      </div>

                      {!isCompact && (
                        <div className="text-xs text-[#8696a0] truncate mt-1">
                          <span className="opacity-70 mr-1">{previewIcon}</span>
                          {l.ultima_msg || '(Sem mensagens)'}
                        </div>
                      )}

                      {!isCompact && (
                        <div className="flex gap-1.5 mt-2 flex-wrap">
                          {l.spiritual_category && (
                            <span
                              className={`text-[8px] uppercase tracking-widest px-1.5 py-0.5 rounded-md font-bold border flex items-center gap-1 ${
                                l.spiritual_urgency === 'high'
                                  ? 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                                  : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                              }`}
                            >
                              {INTENT_EMOJI[l.spiritual_category] || '✦'}
                              {l.spiritual_category}
                            </span>
                          )}
                          {l.bot_pausado && (
                            <span className="bg-amber-500/10 text-amber-400 text-[8px] uppercase tracking-wider px-1.5 py-0.5 rounded-md font-bold border border-amber-500/30">
                              Atendente
                            </span>
                          )}
                          {l.is_urgent && (
                            <span
                              className="bg-red-500/15 text-red-400 text-[8px] uppercase tracking-wider px-1.5 py-0.5 rounded-md font-bold border border-red-500/30 flex items-center gap-1 animate-pulse"
                              title={l.urgent_reason || 'Lead em crise detectada pela IA'}
                            >
                              <AlertTriangle className="w-2.5 h-2.5" />
                              Urgente
                            </span>
                          )}
                          {l.convertido && (
                            <span className="bg-[#00a884]/15 text-[#00a884] text-[8px] uppercase tracking-wider px-1.5 py-0.5 rounded-md font-bold border border-[#00a884]/30">
                              Convertido
                            </span>
                          )}
                          {(l.tags || []).slice(0, 2).map((tag) => (
                            <span
                              key={tag}
                              className="bg-[#202c33] text-[#8696a0] text-[8px] uppercase tracking-wider px-1.5 py-0.5 rounded-md font-bold border border-[#2a3942]"
                            >
                              #{tag}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
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
          /* Visualização de Chat Unificada Estilo WhatsApp Web Pro */
          <div className="flex-1 flex flex-col h-full bg-[#0b141a] animate-in slide-in-from-right-4 duration-300">
            {!selectedLeadId ? (
              <div className="flex-1 flex flex-col items-center justify-center p-8 text-center bg-[#0b141a] bg-[radial-gradient(#1f2c34_1px,transparent_1px)] [background-size:20px_20px]">
                <div className="w-20 h-20 rounded-3xl bg-[#202c33] border border-[#2a3942] flex items-center justify-center mb-6 shadow-2xl ring-1 ring-white/5">
                  <MessageSquare className="w-10 h-10 text-[#00a884]" />
                </div>
                <h3 className="text-2xl font-bold text-[#e9edef] mb-2 tracking-tight">Acássia · Central de Conversas</h3>
                <p className="text-sm text-[#8696a0] max-w-md mb-6 leading-relaxed">
                  Selecione uma conversa na lista à esquerda para interagir, monitorar a IA em tempo real ou assumir o atendimento humano.
                </p>
                <div className="flex items-center gap-4 text-xs text-[#8696a0]">
                  <span className="flex items-center gap-1.5"><kbd className="px-2 py-1 rounded-md bg-[#202c33] border border-[#2a3942] text-[#e9edef] font-mono text-[11px]">/</kbd> buscar</span>
                  <span className="flex items-center gap-1.5"><kbd className="px-2 py-1 rounded-md bg-[#202c33] border border-[#2a3942] text-[#e9edef] font-mono text-[11px]">j/k</kbd> navegar</span>
                  <span className="flex items-center gap-1.5"><kbd className="px-2 py-1 rounded-md bg-[#202c33] border border-[#2a3942] text-[#e9edef] font-mono text-[11px]">Esc</kbd> fechar</span>
                </div>
                <button 
                  onClick={() => setViewMode('table')}
                  className="mt-8 flex items-center gap-2 text-xs font-bold text-[#00a884] hover:text-[#06cf9c] px-4 py-2 rounded-xl bg-[#202c33] border border-[#2a3942] hover:border-[#00a884]/40 transition-all shadow-sm"
                >
                  <LayoutList className="w-4 h-4" />
                  Visualizar todos os contatos em tabela
                </button>
              </div>
            ) : (
              <WhatsAppChatView
                selectedLeadId={selectedLeadId}
                selectedLead={selectedLead}
                messages={messages}
                draft={draft}
                setDraft={setDraft}
                handleSend={handleSend}
                isSending={sendMutation.isPending}
                onToggleTakeover={() => takeoverMutation.mutate(selectedLeadId)}
                isTogglingTakeover={takeoverMutation.isPending}
                voiceOnlyMode={voiceOnlyMode}
                setVoiceOnlyMode={setVoiceOnlyMode}
                typingLeadIds={typingLeadIds}
                quickReplies={quickReplies?.quick_replies}
                onInsertQuickReply={insertAtCursor}
                onOpenQuickReplyManager={() => setShowQuickReplyManager(true)}
                onOpenAudioCompose={() => setShowAudioCompose(true)}
                chatContainerRef={chatContainerRef}
                handleChatScroll={handleChatScroll}
                messagesEndRef={messagesEndRef}
                showScrollBtn={showScrollBtn}
                scrollToBottom={scrollToBottom}
                onReprocessLast={() => {
                  if (selectedLeadId) {
                    inboxApi.resumeLastUser(selectedLeadId).then(() => {
                      queryClient.invalidateQueries({ queryKey: ['leads-conversation', selectedLeadId] });
                    });
                  }
                }}
                onResendCurrentBlock={() => {
                  if (selectedLeadId) {
                    inboxApi.resendCurrentBlock(selectedLeadId).then(() => {
                      queryClient.invalidateQueries({ queryKey: ['leads-conversation', selectedLeadId] });
                    });
                  }
                }}
                onToggleContextPanel={() => setShowLeadDrawer((v) => !v)}
                showContextPanel={showLeadDrawer}
              />
            )}
          </div>
        )}
      </div>

      {showQuickReplyManager && (
        <QuickReplyManager onClose={() => setShowQuickReplyManager(false)} />
      )}

      {showAudioCompose && selectedLeadId !== null && (
        <AudioComposeModal
          leadId={selectedLeadId}
          leadName={selectedLead?.nome || selectedLead?.telefone || 'lead'}
          onClose={() => setShowAudioCompose(false)}
          onSent={() => {
            queryClient.invalidateQueries({ queryKey: ['leads-conversation', selectedLeadId] });
            queryClient.invalidateQueries({ queryKey: ['leads-list'] });
          }}
        />
      )}

      {/* 3ª coluna: Contexto do lead — só no chat mode com lead selecionado */}
      {viewMode === 'chat' && selectedLeadId !== null && showLeadDrawer && (
        <div className="hidden lg:block w-[340px] flex-shrink-0 border-l border-[#2a3942] bg-[#111b21] overflow-y-auto">
          <div className="p-3 border-b border-[#2a3942] bg-[#202c33]/70 flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase tracking-wider text-[#8696a0]">
              Detalhes do Lead
            </h3>
            <button
              onClick={() => setShowLeadDrawer(false)}
              className="p-1 hover:bg-[#2a3942] rounded-lg text-[#8696a0] hover:text-[#e9edef] transition-colors"
              title="Fechar painel"
            >
              ✕
            </button>
          </div>
          <LeadContextPanel leadId={selectedLeadId} />
        </div>
      )}
    </div>
  );
}
