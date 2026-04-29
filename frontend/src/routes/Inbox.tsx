import { useState, useRef, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { inboxApi } from '../api/inbox';
import { toast } from '../lib/toast';
import { Clock, MessageSquare, PauseCircle, PlayCircle, Send, User } from 'lucide-react';

export default function Inbox() {
  const [filtro, setFiltro] = useState('todos');
  const [selectedLeadId, setSelectedLeadId] = useState<number | null>(null);
  const [draft, setDraft] = useState('');
  const queryClient = useQueryClient();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const { data: leadsData, isLoading: isLoadingLeads } = useQuery({
    queryKey: ['inbox-leads', filtro],
    queryFn: () => inboxApi.getLeads(filtro),
    refetchInterval: 10000,
  });

  const { data: conversationData, isLoading: isLoadingConv } = useQuery({
    queryKey: ['inbox-conversation', selectedLeadId],
    queryFn: () => inboxApi.getConversation(selectedLeadId!),
    enabled: selectedLeadId !== null,
    refetchInterval: 5000,
  });

  const takeoverMutation = useMutation({
    mutationFn: inboxApi.toggleTakeover,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['inbox-conversation', selectedLeadId] });
      queryClient.invalidateQueries({ queryKey: ['inbox-leads'] });
    },
    onError: (e) => toast.error((e as Error).message),
  });

  const sendMutation = useMutation({
    mutationFn: ({ leadId, text }: { leadId: number; text: string }) =>
      inboxApi.sendMessage(leadId, text),
    onSuccess: () => {
      setDraft('');
      queryClient.invalidateQueries({ queryKey: ['inbox-conversation', selectedLeadId] });
      queryClient.invalidateQueries({ queryKey: ['inbox-leads'] });
    },
    onError: (e) => toast.error(`Falha ao enviar: ${(e as Error).message}`),
  });

  const handleSend = () => {
    const text = draft.trim();
    if (!text || selectedLeadId == null) return;
    if (!lead?.bot_pausado) {
      if (!confirm('O bot ainda está ativo neste lead. Enviar mesmo assim pode atropelar a conversa do robô. Continuar?'))
        return;
    }
    sendMutation.mutate({ leadId: selectedLeadId, text });
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [conversationData?.messages]);

  const leads = leadsData?.items || [];
  const lead = conversationData?.lead;
  const messages = conversationData?.messages || [];

  return (
    <div className="flex h-full w-full bg-sibila-onyx text-sibila-moonlight">
      {/* Left Sidebar (Leads List) */}
      <div className="w-[340px] flex-shrink-0 flex flex-col border-r border-sibila-mist bg-sibila-obsidian">
        <div className="p-4 border-b border-sibila-mist flex-shrink-0">
          <h2 className="text-lg font-bold mb-3">Caixa de Entrada</h2>
          <div className="flex bg-sibila-obsidian/60 p-1 rounded-lg">
            {['todos', 'ativas', 'pausadas'].map((f) => (
              <button
                key={f}
                onClick={() => setFiltro(f)}
                className={`flex-1 text-xs font-semibold py-1.5 rounded-md capitalize transition-colors ${
                  filtro === f ? 'bg-sibila-amethyst text-white shadow-sm' : 'text-sibila-fog hover:text-sibila-moonlight'
                }`}
              >
                {f}
              </button>
            ))}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {isLoadingLeads ? (
            <div className="p-4 text-center text-sibila-smoke text-sm">Carregando leads...</div>
          ) : leads.length === 0 ? (
            <div className="p-4 text-center text-sibila-smoke text-sm">Nenhum lead encontrado.</div>
          ) : (
            leads.map((l) => (
              <div
                key={l.id}
                onClick={() => setSelectedLeadId(l.id)}
                className={`p-4 border-b border-sibila-mist cursor-pointer transition-colors border-l-[3px] ${
                  selectedLeadId === l.id
                    ? 'bg-sibila-amethyst/10 border-l-sibila-amethyst'
                    : 'border-l-transparent hover:bg-sibila-obsidian/60'
                }`}
              >
                <div className="flex justify-between items-start mb-1">
                  <div className="font-semibold text-sm truncate pr-2">
                    {l.nome || l.telefone}
                  </div>
                  {l.ultima_em && (
                    <div className="text-[10px] text-sibila-smoke flex-shrink-0">
                      {new Date(l.ultima_em).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </div>
                  )}
                </div>
                <div className="text-xs text-sibila-fog line-clamp-1 mb-2">
                  {l.ultima_msg || '(sem mensagens)'}
                </div>
                <div className="flex items-center gap-2">
                  {l.bot_pausado && (
                    <span className="bg-amber-500/10 text-amber-400 text-[9px] uppercase tracking-wider px-1.5 py-0.5 rounded font-bold">
                      Pausado
                    </span>
                  )}
                  {l.opt_out && (
                    <span className="bg-red-500/10 text-red-400 text-[9px] uppercase tracking-wider px-1.5 py-0.5 rounded font-bold">
                      Opt-out
                    </span>
                  )}
                  {l.convertido && (
                    <span className="bg-emerald-500/10 text-emerald-400 text-[9px] uppercase tracking-wider px-1.5 py-0.5 rounded font-bold">
                      Convertido
                    </span>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Right Area (Conversation) */}
      <div className="flex-1 flex flex-col min-w-0 bg-[#f5f7fc]">
        {!selectedLeadId ? (
          <div className="flex-1 flex flex-col items-center justify-center text-sibila-fog bg-sibila-onyx">
            <MessageSquare className="w-12 h-12 mb-4 opacity-20" />
            <p>Selecione uma conversa para visualizar</p>
          </div>
        ) : isLoadingConv ? (
          <div className="flex-1 flex items-center justify-center text-sibila-fog bg-sibila-onyx">
            Carregando conversa...
          </div>
        ) : (
          <>
            {/* Chat Header */}
            <div className="h-[60px] px-6 bg-white border-b border-slate-200 flex items-center justify-between shadow-sm z-10 flex-shrink-0">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-sibila-amethyst/10 text-sibila-amethyst flex items-center justify-center font-bold">
                  <User className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-bold text-slate-800 leading-tight">{lead?.nome || lead?.telefone}</h3>
                  <div className="text-[11px] text-sibila-smoke font-mono">{lead?.telefone} · {lead?.node_atual || 'Início'}</div>
                </div>
              </div>
              <div>
                <button
                  onClick={() => takeoverMutation.mutate(selectedLeadId)}
                  disabled={takeoverMutation.isPending}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-bold transition-all ${
                    lead?.bot_pausado
                      ? 'bg-emerald-50 text-emerald-600 border border-emerald-200 hover:bg-emerald-100'
                      : 'bg-amber-50 text-amber-600 border border-amber-200 hover:bg-amber-100'
                  }`}
                >
                  {lead?.bot_pausado ? (
                    <>
                      <PlayCircle className="w-4 h-4" />
                      Liberar Robô
                    </>
                  ) : (
                    <>
                      <PauseCircle className="w-4 h-4" />
                      Pausar Robô (Assumir)
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Chat Messages */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4 bg-gradient-to-b from-[#f8f9fd] to-[#f5f7fc]">
              <div className="text-center my-4">
                <span className="bg-white border border-slate-200 text-sibila-fog text-[10px] uppercase tracking-widest font-bold px-3 py-1 rounded-full shadow-sm">
                  Início da Conversa
                </span>
              </div>
              
              {messages.map((m) => {
                const isUser = m.origem === 'lead';
                const isSystem = m.origem === 'system';
                
                if (isSystem) {
                  return (
                    <div key={m.id} className="flex justify-center my-2">
                      <div className="bg-[#fff1f1] border border-[#ffd9d9] text-[#8b3e3e] text-[11px] italic px-3 py-1.5 rounded-lg shadow-sm">
                        {m.texto}
                      </div>
                    </div>
                  );
                }

                return (
                  <div key={m.id} className={`flex ${isUser ? 'justify-start' : 'justify-end'}`}>
                    <div className="flex flex-col max-w-[70%]">
                      <div
                        className={`px-4 py-2 text-[13px] shadow-sm relative ${
                          isUser
                            ? 'bg-white border border-slate-200 text-slate-800 rounded-2xl rounded-tl-sm'
                            : 'bg-[#eef8f2] border border-[#cfe9da] text-[#284f3e] rounded-2xl rounded-tr-sm'
                        }`}
                      >
                        {m.media_type && (
                          <div className="text-[10px] uppercase tracking-wider text-sibila-amethyst mb-1 font-bold">
                            {m.media_type}
                          </div>
                        )}
                        <div className="whitespace-pre-wrap break-words">{m.texto || '(Mídia)'}</div>
                        <div className={`text-[9px] mt-1 text-right flex items-center justify-end gap-1 ${isUser ? 'text-sibila-fog' : 'text-[#5b9679]'}`}>
                          {m.timestamp && new Date(m.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          {!isUser && <Clock className="w-2.5 h-2.5 inline" />}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
              <div ref={messagesEndRef} />
            </div>

            {/* Chat Input — manda via /api/leads/:id/send */}
            <div className="bg-white border-t border-slate-200 p-3 flex-shrink-0 z-10 space-y-2">
              <div className="flex items-center gap-3">
                <input
                  type="text"
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleSend();
                    }
                  }}
                  placeholder={
                    lead?.bot_pausado
                      ? 'Mensagem manual (Enter envia)…'
                      : 'Pause o bot pra assumir, ou envie mesmo assim…'
                  }
                  disabled={sendMutation.isPending}
                  className="flex-1 bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-800 outline-none focus:border-sibila-amethyst disabled:opacity-60"
                />
                <button
                  onClick={handleSend}
                  disabled={sendMutation.isPending || !draft.trim()}
                  className="w-10 h-10 bg-sibila-amethyst text-white rounded-xl flex items-center justify-center hover:brightness-110 disabled:bg-sibila-amethyst/40 disabled:cursor-not-allowed"
                  title="Enviar (Enter)"
                >
                  <Send className="w-4 h-4" />
                </button>
              </div>
              {selectedLeadId != null && (
                <div className="flex items-center justify-end gap-2 text-[11px]">
                  <button
                    onClick={() => inboxApi.resumeLastUser(selectedLeadId).then(() => {
                      toast.success('Reprocessando última mensagem do lead.');
                      queryClient.invalidateQueries({ queryKey: ['inbox-conversation', selectedLeadId] });
                    }).catch((e) => toast.error((e as Error).message))}
                    className="text-sibila-smoke hover:text-sibila-amethyst"
                    title="Roda de novo a última mensagem do lead pelo motor"
                  >
                    ↻ reprocessar última
                  </button>
                  <span className="text-sibila-fog">·</span>
                  <button
                    onClick={() => inboxApi.resendCurrentBlock(selectedLeadId).then(() => {
                      toast.success('Reenviando bloco atual.');
                      queryClient.invalidateQueries({ queryKey: ['inbox-conversation', selectedLeadId] });
                    }).catch((e) => toast.error((e as Error).message))}
                    className="text-sibila-smoke hover:text-sibila-amethyst"
                    title="Reenvia o bloco atual do funil"
                  >
                    ⟳ reenviar bloco
                  </button>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
