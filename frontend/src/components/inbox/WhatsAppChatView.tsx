import { useState, useRef, useMemo } from 'react';
import {
  Check,
  CheckCheck,
  Clock,
  AlertCircle,
  User,
  Bot,
  Play,
  Pause,
  Volume2,
  Tag,
  Send,
  PlayCircle,
  PauseCircle,
  Mic,
  MicOff,
  MoreVertical,
  RotateCcw,
  RefreshCw,
  Zap,
  MessageSquare,
  X,
  Info,
} from 'lucide-react';
import type { LeadDetail, LeadMessage } from '../../api/inbox';
import type { QuickReply } from '../../api/compose';
import ComposeToolbar from '../ComposeToolbar';
import ScrollToBottom from './ScrollToBottom';
import TypingIndicator from './TypingIndicator';
import VoiceOnlyCompose from '../VoiceOnlyCompose';

interface Props {
  selectedLeadId: number;
  selectedLead: LeadDetail | undefined;
  messages: LeadMessage[];
  draft: string;
  setDraft: (draft: string) => void;
  handleSend: () => void;
  isSending: boolean;
  onToggleTakeover: () => void;
  isTogglingTakeover: boolean;
  voiceOnlyMode: boolean;
  setVoiceOnlyMode: React.Dispatch<React.SetStateAction<boolean>>;
  typingLeadIds: Set<number>;
  quickReplies: QuickReply[] | undefined;
  onInsertQuickReply: (text: string) => void;
  onOpenQuickReplyManager: () => void;
  onOpenAudioCompose: () => void;
  chatContainerRef: React.RefObject<HTMLDivElement>;
  handleChatScroll: () => void;
  messagesEndRef: React.RefObject<HTMLDivElement>;
  showScrollBtn: boolean;
  scrollToBottom: () => void;
  onReprocessLast: () => void;
  onResendCurrentBlock: () => void;
  onToggleContextPanel?: () => void;
  showContextPanel?: boolean;
}

// Status de Entrega WhatsApp (Ticks)
export function WhatsAppDeliveryCheckmark({ status }: { status?: string | null }) {
  if (!status || status === 'pending') {
    return (
      <span className="flex items-center text-[#8696a0]" title="Enviando...">
        <Clock className="w-3 h-3" />
      </span>
    );
  }
  if (status === 'failed') {
    return (
      <span className="flex items-center text-rose-400" title="Falha ao entregar">
        <AlertCircle className="w-3 h-3" />
      </span>
    );
  }
  if (status === 'read') {
    return (
      <span className="flex items-center text-[#53bdeb]" title="Mensagem lida">
        <CheckCheck className="w-3.5 h-3.5 stroke-[2.5]" />
      </span>
    );
  }
  if (status === 'delivered') {
    return (
      <span className="flex items-center text-[#8696a0]" title="Entregue">
        <CheckCheck className="w-3.5 h-3.5 stroke-[2.5]" />
      </span>
    );
  }
  // sent
  return (
    <span className="flex items-center text-[#8696a0]" title="Enviada ao servidor">
      <Check className="w-3.5 h-3.5 stroke-[2.5]" />
    </span>
  );
}

// Mini Player de Áudio WhatsApp
function AudioMessagePlayer({ url }: { url: string }) {
  const [playing, setPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const toggle = () => {
    if (!audioRef.current) return;
    if (playing) {
      audioRef.current.pause();
      setPlaying(false);
    } else {
      audioRef.current.play().catch(() => {});
      setPlaying(true);
    }
  };

  const handleTimeUpdate = () => {
    if (!audioRef.current || !audioRef.current.duration) return;
    setProgress((audioRef.current.currentTime / audioRef.current.duration) * 100);
  };

  return (
    <div className="flex items-center gap-3 py-1.5 px-2 bg-black/20 rounded-xl my-1 min-w-[210px] max-w-[270px]">
      <audio
        ref={audioRef}
        src={url}
        onTimeUpdate={handleTimeUpdate}
        onEnded={() => { setPlaying(false); setProgress(0); }}
        className="hidden"
      />
      <button
        type="button"
        onClick={toggle}
        className="w-9 h-9 rounded-full bg-[#00a884] hover:bg-[#06cf9c] text-zinc-950 flex items-center justify-center flex-shrink-0 transition-transform active:scale-95 shadow"
      >
        {playing ? <Pause className="w-4 h-4 fill-current" /> : <Play className="w-4 h-4 fill-current ml-0.5" />}
      </button>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-0.5 h-4 mb-1">
          {[35, 60, 25, 80, 50, 95, 40, 70, 85, 30, 90, 45, 65, 80, 35, 60, 75, 40].map((h, i) => {
            const barPercent = (i / 18) * 100;
            const isPlayed = progress >= barPercent;
            return (
              <div
                key={i}
                className={`w-1 rounded-full transition-colors ${
                  isPlayed ? 'bg-[#53bdeb]' : 'bg-white/30'
                }`}
                style={{ height: `${h}%` }}
              />
            );
          })}
        </div>
        <div className="flex justify-between items-center text-[10px] text-zinc-300 font-mono">
          <span>Áudio WhatsApp</span>
          <Volume2 className="w-3 h-3 opacity-60" />
        </div>
      </div>
    </div>
  );
}

// Visualizador de Imagem WhatsApp
function ImageMessageBubble({ url }: { url: string }) {
  const [openModal, setOpenModal] = useState(false);
  return (
    <div className="space-y-1.5 mb-1">
      <img
        src={url}
        alt="Mídia WhatsApp"
        onClick={() => setOpenModal(true)}
        className="rounded-xl max-h-64 object-cover cursor-pointer hover:opacity-95 transition-opacity border border-black/20"
      />
      {openModal && (
        <div
          className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center p-4 backdrop-blur-sm animate-fade-in"
          onClick={() => setOpenModal(false)}
        >
          <div className="relative max-w-4xl max-h-[90vh]">
            <img src={url} alt="Imagem ampliada" className="max-w-full max-h-[85vh] rounded-2xl shadow-2xl" />
            <button
              onClick={() => setOpenModal(false)}
              className="absolute -top-3 -right-3 w-8 h-8 rounded-full bg-zinc-800 text-white flex items-center justify-center hover:bg-zinc-700"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// Auxiliares de Data e Avatar
function formatDateDivider(dateStr: string | null): string {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  const today = new Date();
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);

  if (d.toDateString() === today.toDateString()) {
    return 'Hoje';
  }
  if (d.toDateString() === yesterday.toDateString()) {
    return 'Ontem';
  }
  return d.toLocaleDateString('pt-BR', {
    day: 'numeric',
    month: 'long',
    year: d.getFullYear() !== today.getFullYear() ? 'numeric' : undefined,
  });
}

function formatTime(dateStr: string | null): string {
  if (!dateStr) return '';
  return new Date(dateStr).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function getInitials(name?: string, phone?: string): string {
  if (!name || name.trim().length === 0) {
    return phone ? phone.slice(-2) : 'WA';
  }
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

function getAvatarGradient(name?: string, phone?: string): string {
  const str = name || phone || 'Lead';
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  const gradients = [
    'from-emerald-600 to-teal-700',
    'from-indigo-600 to-purple-700',
    'from-blue-600 to-cyan-700',
    'from-amber-600 to-orange-700',
    'from-rose-600 to-pink-700',
    'from-violet-600 to-fuchsia-700',
  ];
  return gradients[Math.abs(hash) % gradients.length];
}

// COMPONENTE PRINCIPAL WHATSAPP CONVERSATION VIEW
export default function WhatsAppChatView({
  selectedLeadId,
  selectedLead,
  messages,
  draft,
  setDraft,
  handleSend,
  isSending,
  onToggleTakeover,
  isTogglingTakeover,
  voiceOnlyMode,
  setVoiceOnlyMode,
  typingLeadIds,
  quickReplies,
  onInsertQuickReply,
  onOpenQuickReplyManager,
  onOpenAudioCompose,
  chatContainerRef,
  handleChatScroll,
  messagesEndRef,
  showScrollBtn,
  scrollToBottom,
  onReprocessLast,
  onResendCurrentBlock,
  onToggleContextPanel,
  showContextPanel = true,
}: Props) {
  const [showMoreActions, setShowMoreActions] = useState(false);
  const avatarGradient = useMemo(
    () => getAvatarGradient(selectedLead?.nome, selectedLead?.telefone),
    [selectedLead?.nome, selectedLead?.telefone]
  );
  const initials = useMemo(
    () => getInitials(selectedLead?.nome, selectedLead?.telefone),
    [selectedLead?.nome, selectedLead?.telefone]
  );

  // Agrupamento de mensagens por data para divisores centrais
  const messagesWithDateDividers = useMemo(() => {
    const result: Array<{ type: 'date'; date: string } | { type: 'msg'; msg: LeadMessage }> = [];
    let lastDate = '';

    for (const m of messages) {
      const divider = formatDateDivider(m.timestamp);
      if (divider && divider !== lastDate) {
        result.push({ type: 'date', date: divider });
        lastDate = divider;
      }
      result.push({ type: 'msg', msg: m });
    }
    return result;
  }, [messages]);

  const defaultQuickPills = [
    { label: '⚡ Olá! Como posso ajudar?', text: 'Olá! Tudo bem? Como posso te ajudar hoje?' },
    { label: '💳 Link de Pagamento', text: 'Você pode concluir o seu pagamento com segurança através deste link:' },
    { label: '📅 Agendar Demonstração', text: 'Qual é o melhor horário para conversarmos rapidamente hoje?' },
    { label: '📄 Enviar Catálogo', text: 'Estou te enviando as opções e condições especiais disponíveis agora.' },
  ];

  return (
    <div className="flex-1 flex flex-col h-full bg-[#0b141a] relative overflow-hidden">
      {/* 1. Header estilo WhatsApp Web Pro */}
      <div className="h-[68px] px-5 bg-[#202c33] border-b border-[#2a3942] flex items-center justify-between z-10 flex-shrink-0 shadow-sm">
        <div className="flex items-center gap-3.5 min-w-0">
          <div className="relative flex-shrink-0">
            <div
              className={`w-11 h-11 rounded-full bg-gradient-to-tr ${avatarGradient} flex items-center justify-center font-black text-white text-sm shadow-md ring-2 ring-white/10`}
            >
              {initials}
            </div>
            <span
              className="w-3 h-3 rounded-full bg-emerald-500 border-2 border-[#202c33] absolute bottom-0 right-0"
              title="Online no WhatsApp"
            />
          </div>

          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h3 className="font-bold text-[#e9edef] text-base leading-tight truncate tracking-tight">
                {selectedLead?.nome || selectedLead?.telefone}
              </h3>
              {selectedLead?.bot_pausado ? (
                <span className="text-[10px] font-bold uppercase tracking-wider bg-amber-500/15 text-amber-300 border border-amber-500/30 px-2 py-0.5 rounded-full flex items-center gap-1">
                  <User className="w-2.5 h-2.5" />
                  Atendente
                </span>
              ) : (
                <span className="text-[10px] font-bold uppercase tracking-wider bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 px-2 py-0.5 rounded-full flex items-center gap-1">
                  <Bot className="w-2.5 h-2.5" />
                  Robô IA
                </span>
              )}
            </div>

            <div className="flex items-center gap-2 text-[11px] text-[#8696a0] mt-0.5 truncate">
              <span>{selectedLead?.telefone}</span>
              {selectedLead?.node_atual && (
                <>
                  <span className="w-1 h-1 rounded-full bg-[#8696a0]" />
                  <span className="text-[#00a884] font-medium flex items-center gap-1">
                    <Tag className="w-2.5 h-2.5" />
                    {selectedLead.node_atual}
                  </span>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Controles e Ações Rápidas */}
        <div className="flex items-center gap-2 flex-shrink-0">
          <button
            onClick={onToggleTakeover}
            disabled={isTogglingTakeover}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all shadow-sm border active:scale-95 ${
              selectedLead?.bot_pausado
                ? 'bg-emerald-600 hover:bg-emerald-500 text-white border-emerald-500 shadow-emerald-950/20'
                : 'bg-[#2a3942] hover:bg-[#3b4a54] text-amber-400 border-amber-500/30'
            }`}
          >
            {selectedLead?.bot_pausado ? (
              <>
                <PlayCircle className="w-4 h-4 text-white" />
                <span>Liberar Robô</span>
              </>
            ) : (
              <>
                <PauseCircle className="w-4 h-4 text-amber-400" />
                <span>Assumir Chat</span>
              </>
            )}
          </button>

          <button
            onClick={() => setVoiceOnlyMode((v) => !v)}
            title={voiceOnlyMode ? 'Sair do modo áudio contínuo' : 'Ativar modo áudio'}
            className={`p-2 rounded-xl border transition-all ${
              voiceOnlyMode
                ? 'bg-emerald-600 text-white border-emerald-500 shadow-md'
                : 'bg-[#2a3942] border-transparent hover:border-[#3b4a54] text-[#aebac1]'
            }`}
          >
            {voiceOnlyMode ? <Mic className="w-4 h-4" /> : <MicOff className="w-4 h-4" />}
          </button>

          {onToggleContextPanel && (
            <button
              onClick={onToggleContextPanel}
              title={showContextPanel ? 'Ocultar detalhes do lead' : 'Ver detalhes do lead'}
              className={`p-2 rounded-xl border transition-all ${
                showContextPanel
                  ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                  : 'bg-[#2a3942] border-transparent hover:border-[#3b4a54] text-[#aebac1]'
              }`}
            >
              <Info className="w-4 h-4" />
            </button>
          )}

          <div className="relative">
            <button
              onClick={() => setShowMoreActions((v) => !v)}
              className="p-2 rounded-xl bg-[#2a3942] hover:bg-[#3b4a54] text-[#aebac1] transition-all"
            >
              <MoreVertical className="w-4 h-4" />
            </button>
            {showMoreActions && (
              <div className="absolute right-0 mt-2 w-52 bg-[#202c33] border border-[#2a3942] rounded-2xl shadow-2xl p-1.5 z-50 text-xs text-[#d1d7db] animate-fade-in">
                <button
                  onClick={() => {
                    onReprocessLast();
                    setShowMoreActions(false);
                  }}
                  className="w-full text-left px-3 py-2 rounded-xl hover:bg-[#2a3942] flex items-center gap-2"
                >
                  <RotateCcw className="w-3.5 h-3.5 text-emerald-400" />
                  Reprocessar Última Msg
                </button>
                <button
                  onClick={() => {
                    onResendCurrentBlock();
                    setShowMoreActions(false);
                  }}
                  className="w-full text-left px-3 py-2 rounded-xl hover:bg-[#2a3942] flex items-center gap-2"
                >
                  <RefreshCw className="w-3.5 h-3.5 text-sky-400" />
                  Reenviar Bloco Atual
                </button>
                <button
                  onClick={() => {
                    onOpenQuickReplyManager();
                    setShowMoreActions(false);
                  }}
                  className="w-full text-left px-3 py-2 rounded-xl hover:bg-[#2a3942] flex items-center gap-2"
                >
                  <Zap className="w-3.5 h-3.5 text-amber-400" />
                  Gerenciar Respostas Rápidas
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 2. Corpo do chat com textura WhatsApp */}
      <div
        ref={chatContainerRef}
        onScroll={handleChatScroll}
        className="flex-1 overflow-y-auto px-4 sm:px-8 py-6 space-y-3 relative bg-[#0b141a] bg-[radial-gradient(#1f2c34_1px,transparent_1px)] [background-size:20px_20px]"
      >
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center text-[#8696a0] space-y-2 opacity-60">
            <MessageSquare className="w-12 h-12 stroke-[1.2]" />
            <p className="text-sm font-medium">Nenhuma mensagem registrada nesta conversa ainda.</p>
            <p className="text-xs">Inicie o atendimento digitando abaixo.</p>
          </div>
        ) : (
          messagesWithDateDividers.map((item, idx) => {
            if (item.type === 'date') {
              return (
                <div key={`date-${idx}`} className="flex justify-center my-3">
                  <div className="bg-[#182229]/95 border border-[#222e35] text-zinc-300 text-[11px] font-semibold px-3.5 py-1 rounded-full shadow-sm backdrop-blur-sm">
                    {item.date}
                  </div>
                </div>
              );
            }

            const m = item.msg;
            const isUser = m.origem === 'lead';
            const isSystem = m.origem === 'system';

            if (isSystem) {
              return (
                <div key={m.id} className="flex justify-center my-2">
                  <div className="bg-[#182229]/80 border border-[#222e35] text-zinc-300 text-xs px-3.5 py-1.5 rounded-xl shadow-sm text-center max-w-md">
                    {m.texto}
                  </div>
                </div>
              );
            }

            const isAudio =
              m.media_type?.includes('audio') ||
              m.media_url?.match(/\.(mp3|ogg|wav|m4a)/i) ||
              m.texto === '(Áudio)';
            const isImage =
              m.media_type?.includes('image') ||
              m.media_url?.match(/\.(jpg|jpeg|png|webp|gif)/i);

            return (
              <div key={m.id} className={`flex ${isUser ? 'justify-start' : 'justify-end'} my-1`}>
                <div
                  className={`flex flex-col max-w-[85%] sm:max-w-[70%] ${
                    isUser ? 'items-start' : 'items-end'
                  }`}
                >
                  <div
                    className={`px-3.5 py-2 text-sm shadow-md relative break-words leading-relaxed ${
                      isUser
                        ? 'bg-[#202c33] text-[#e9edef] rounded-2xl rounded-tl-xs border border-[#2a3942]/60'
                        : 'bg-[#005c4b] text-[#e9edef] rounded-2xl rounded-tr-xs border border-[#00705a]/60 shadow-[#005c4b]/10'
                    }`}
                  >
                    {!isUser && (
                      <div className="flex items-center justify-between gap-3 mb-1 text-[10px] font-semibold text-emerald-200/80 border-b border-emerald-600/30 pb-0.5">
                        <span className="flex items-center gap-1">
                          {m.origem === 'bot' ? (
                            <>
                              <Bot className="w-3 h-3 text-emerald-300" />
                              <span>Agente IA</span>
                            </>
                          ) : (
                            <>
                              <User className="w-3 h-3 text-emerald-300" />
                              <span>Você (Atendente)</span>
                            </>
                          )}
                        </span>
                      </div>
                    )}

                    {isAudio && m.media_url ? (
                      <AudioMessagePlayer url={m.media_url} />
                    ) : isImage && m.media_url ? (
                      <ImageMessageBubble url={m.media_url} />
                    ) : null}

                    {m.texto && (!isAudio || m.texto !== '(Áudio)') && (
                      <div className="whitespace-pre-wrap font-normal select-text">
                        {m.texto}
                      </div>
                    )}

                    <div
                      className={`flex items-center justify-end gap-1.5 text-[10px] font-mono mt-1 select-none ${
                        isUser ? 'text-[#8696a0]' : 'text-emerald-100/70'
                      }`}
                    >
                      <span>{formatTime(m.timestamp)}</span>
                      {!isUser && <WhatsAppDeliveryCheckmark status={m.delivery_status ?? null} />}
                    </div>
                  </div>
                </div>
              </div>
            );
          })
        )}

        {selectedLeadId && typingLeadIds.has(selectedLeadId) && (
          <TypingIndicator name={selectedLead?.nome || undefined} />
        )}

        <div ref={messagesEndRef} />
        <ScrollToBottom visible={showScrollBtn} onClick={scrollToBottom} />
      </div>

      {/* 3. Barra de Respostas Rápidas */}
      <div className="bg-[#1f2c34] border-t border-[#2a3942] px-4 py-2 flex items-center gap-2 overflow-x-auto scrollbar-none flex-shrink-0">
        <span className="text-[10px] font-black uppercase tracking-wider text-[#8696a0] flex items-center gap-1 flex-shrink-0 mr-1">
          <Zap className="w-3 h-3 text-amber-400" />
          Atalhos:
        </span>
        {(quickReplies && quickReplies.length > 0 ? quickReplies.slice(0, 6) : defaultQuickPills).map(
          (qr, i) => {
            const label = String(('title' in qr ? qr.title : (qr as { label: string; text: string }).label) || '');
            const textToInsert = String(('template_text' in qr ? qr.template_text : (qr as { label: string; text: string }).text) || '');
            return (
              <button
                key={i}
                type="button"
                onClick={() => onInsertQuickReply(textToInsert)}
                className="flex-shrink-0 bg-[#2a3942] hover:bg-[#374248] text-[#d1d7db] text-xs font-medium px-3 py-1 rounded-full transition-all border border-transparent hover:border-[#00a884]/40"
              >
                {label}
              </button>
            );
          }
        )}
      </div>

      {/* 4. Barra de Digitação */}
      {voiceOnlyMode ? (
        <VoiceOnlyCompose leadId={selectedLeadId} />
      ) : (
        <div className="bg-[#202c33] border-t border-[#2a3942] p-3 sm:px-5 sm:py-3.5 flex-shrink-0 z-10">
          <div className="max-w-5xl mx-auto">
            <div className="flex items-end gap-2.5">
              <div className="flex items-center gap-1 mb-1">
                <ComposeToolbar
                  leadId={selectedLeadId}
                  onInsert={onInsertQuickReply}
                  onOpenManager={onOpenQuickReplyManager}
                  onOpenAudio={onOpenAudioCompose}
                />
              </div>

              <div className="flex-1 relative">
                <textarea
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
                      ? 'Digite sua mensagem no WhatsApp… (Ctrl+Enter envia)'
                      : 'Robô IA ativo. Digite para responder manualmente...'
                  }
                  rows={Math.min(5, Math.max(1, draft.split('\n').length))}
                  className="w-full bg-[#2a3942] border border-transparent focus:border-[#00a884] rounded-2xl px-4 py-2.5 text-sm text-[#e9edef] placeholder-[#8696a0] outline-none transition-all shadow-inner resize-none leading-relaxed"
                />
                {draft.length > 800 && (
                  <div
                    className={`absolute -top-4 right-3 text-[10px] font-mono font-bold ${
                      draft.length > 1000 ? 'text-rose-400' : 'text-amber-400'
                    }`}
                  >
                    {draft.length}/1000
                  </div>
                )}
              </div>

              <button
                onClick={handleSend}
                disabled={!draft.trim() || isSending}
                className="w-11 h-11 bg-[#00a884] hover:bg-[#06cf9c] text-white rounded-full flex items-center justify-center transition-all shadow-lg shadow-emerald-950/40 active:scale-95 disabled:opacity-30 disabled:scale-100 flex-shrink-0 mb-0.5"
                title="Enviar mensagem (Ctrl+Enter)"
              >
                <Send className="w-4 h-4 ml-0.5" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
