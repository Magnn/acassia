import { useState, useRef, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { inboxApi } from '../api/inbox';
import { User, PauseCircle, PlayCircle, Send, Clock } from 'lucide-react';

export default function Inbox() {
  const [filtro, setFiltro] = useState('todos');
  const [selectedLeadId, setSelectedLeadId] = useState<number | null>(null);
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
  });

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [conversationData?.messages]);

  const leads = leadsData?.items || [];
  const lead = conversationData?.lead;
  const messages = conversationData?.messages || [];

  return (
    <div className="flex h-full w-full bg-cigana-bg text-slate-100">
      {/* Left Sidebar (Leads List) */}
      <div className="w-[340px] flex-shrink-0 flex flex-col border-r border-cigana-border bg-cigana-surface">
        <div className="p-4 border-b border-cigana-border flex-shrink-0">
          <h2 className="text-lg font-bold mb-3">Caixa de Entrada</h2>
          <div className="flex bg-slate-800/50 p-1 rounded-lg">
            {['todos', 'ativas', 'pausadas'].map((f) => (
              <button
                key={f}
                onClick={() => setFiltro(f)}
                className={`flex-1 text-xs font-semibold py-1.5 rounded-md capitalize transition-colors ${
                  filtro === f ? 'bg-cigana-purple text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {f}
              </button>
            ))}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {isLoadingLeads ? (
            <div className="p-4 text-center text-slate-500 text-sm">Carregando leads...</div>
          ) : leads.length === 0 ? (
            <div className="p-4 text-center text-slate-500 text-sm">Nenhum lead encontrado.</div>
          ) : (
            leads.map((l) => (
              <div
                key={l.id}
                onClick={() => setSelectedLeadId(l.id)}
                className={`p-4 border-b border-cigana-border cursor-pointer transition-colors border-l-[3px] ${
                  selectedLeadId === l.id
                    ? 'bg-cigana-purple/10 border-l-cigana-purple'
                    : 'border-l-transparent hover:bg-slate-800/50'
                }`}
              >
                <div className="flex justify-between items-start mb-1">
                  <div className="font-semibold text-sm truncate pr-2">
                    {l.nome || l.telefone}
                  </div>
                  {l.ultima_em && (
                    <div className="text-[10px] text-slate-500 flex-shrink-0">
                      {new Date(l.ultima_em).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </div>
                  )}
                </div>
                <div className="text-xs text-slate-400 line-clamp-1 mb-2">
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
          <div className="flex-1 flex flex-col items-center justify-center text-slate-400 bg-cigana-bg">
            <MessageSquareIcon className="w-12 h-12 mb-4 opacity-20" />
            <p>Selecione uma conversa para visualizar</p>
          </div>
        ) : isLoadingConv ? (
          <div className="flex-1 flex items-center justify-center text-slate-400 bg-cigana-bg">
            Carregando conversa...
          </div>
        ) : (
          <>
            {/* Chat Header */}
            <div className="h-[60px] px-6 bg-white border-b border-slate-200 flex items-center justify-between shadow-sm z-10 flex-shrink-0">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-cigana-purple/10 text-cigana-purple flex items-center justify-center font-bold">
                  <User className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-bold text-slate-800 leading-tight">{lead?.nome || lead?.telefone}</h3>
                  <div className="text-[11px] text-slate-500 font-mono">{lead?.telefone} · {lead?.node_atual || 'Início'}</div>
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
                <span className="bg-white border border-slate-200 text-slate-400 text-[10px] uppercase tracking-widest font-bold px-3 py-1 rounded-full shadow-sm">
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
                          <div className="text-[10px] uppercase tracking-wider text-cigana-purple mb-1 font-bold">
                            {m.media_type}
                          </div>
                        )}
                        <div className="whitespace-pre-wrap break-words">{m.texto || '(Mídia)'}</div>
                        <div className={`text-[9px] mt-1 text-right flex items-center justify-end gap-1 ${isUser ? 'text-slate-400' : 'text-[#5b9679]'}`}>
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

            {/* Chat Input (Disabled for now) */}
            <div className="h-[72px] bg-white border-t border-slate-200 p-4 flex items-center gap-3 flex-shrink-0 z-10">
              <input
                type="text"
                placeholder="A API de envio manual será conectada na Fase 4..."
                disabled
                className="flex-1 bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-sm outline-none cursor-not-allowed opacity-60"
              />
              <button disabled className="w-10 h-10 bg-cigana-purple/50 text-white rounded-xl flex items-center justify-center cursor-not-allowed">
                <Send className="w-4 h-4" />
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function MessageSquareIcon(props: any) {
  return (
    <svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  );
}
