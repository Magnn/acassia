import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { inboxApi } from '../api/inbox';
import { User, MessageSquare, Bot, Search } from 'lucide-react';

export default function Contacts() {
  const [filtro, setFiltro] = useState('todos');

  const { data: leadsData, isLoading } = useQuery({
    queryKey: ['contacts-leads', filtro],
    queryFn: () => inboxApi.getLeads(filtro),
    refetchInterval: 15000,
  });

  const leads = leadsData?.items || [];

  return (
    <div className="p-8 max-w-7xl mx-auto text-slate-100 flex flex-col h-full">
      <div className="flex items-center justify-between mb-8 flex-shrink-0">
        <div>
          <h2 className="text-2xl font-bold font-display">Gestão de Leads (CRM)</h2>
          <p className="text-sm text-slate-400 mt-1">Gerencie os contatos, status e etapas no funil.</p>
        </div>
        <div className="flex bg-cigana-surface border border-cigana-border p-1 rounded-lg">
          {['todos', 'ativas', 'pausadas', 'convertidas', 'perdidas'].map((f) => (
            <button
              key={f}
              onClick={() => setFiltro(f)}
              className={`px-4 py-1.5 text-xs font-semibold rounded-md capitalize transition-colors ${
                filtro === f ? 'bg-cigana-purple text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      <div className="bg-cigana-surface border border-cigana-border rounded-xl flex-1 flex flex-col min-h-0 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-cigana-border flex items-center gap-3">
          <div className="flex items-center gap-2 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 flex-1 max-w-md focus-within:border-cigana-purple transition-colors">
            <Search className="w-4 h-4 text-slate-500" />
            <input 
              type="text" 
              placeholder="Buscar contato (Em breve na Fase 5...)" 
              disabled
              className="bg-transparent border-none outline-none text-sm w-full text-slate-200 placeholder-slate-500"
            />
          </div>
          <div className="text-xs text-slate-500 ml-auto">
            {leads.length} contatos encontrados
          </div>
        </div>

        <div className="flex-1 overflow-auto">
          <table className="w-full text-left border-collapse">
            <thead className="bg-slate-800/40 text-[11px] uppercase tracking-widest text-slate-400 sticky top-0 z-10 backdrop-blur-md">
              <tr>
                <th className="py-3 px-6 font-semibold border-b border-slate-800">Lead</th>
                <th className="py-3 px-6 font-semibold border-b border-slate-800">Status</th>
                <th className="py-3 px-6 font-semibold border-b border-slate-800">Etapa Atual</th>
                <th className="py-3 px-6 font-semibold border-b border-slate-800">Última Interação</th>
                <th className="py-3 px-6 font-semibold border-b border-slate-800 text-right">Ações</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-slate-500">
                    Carregando leads...
                  </td>
                </tr>
              ) : leads.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-slate-500">
                    Nenhum lead encontrado para este filtro.
                  </td>
                </tr>
              ) : (
                leads.map((l) => (
                  <tr key={l.id} className="border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors">
                    <td className="py-3 px-6">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-cigana-bg flex items-center justify-center font-bold text-xs text-slate-300">
                          <User className="w-4 h-4" />
                        </div>
                        <div>
                          <div className="font-semibold text-sm">{l.nome || '(sem nome)'}</div>
                          <div className="text-[11px] text-slate-500 font-mono">{l.telefone}</div>
                        </div>
                      </div>
                    </td>
                    <td className="py-3 px-6">
                      <div className="flex gap-2">
                        {l.convertido && (
                          <span className="bg-emerald-500/10 text-emerald-400 text-[10px] uppercase tracking-wider px-2 py-0.5 rounded font-bold">
                            Convertido
                          </span>
                        )}
                        {l.bot_pausado && (
                          <span className="bg-amber-500/10 text-amber-400 text-[10px] uppercase tracking-wider px-2 py-0.5 rounded font-bold">
                            Pausado
                          </span>
                        )}
                        {l.opt_out && (
                          <span className="bg-red-500/10 text-red-400 text-[10px] uppercase tracking-wider px-2 py-0.5 rounded font-bold">
                            Opt-Out
                          </span>
                        )}
                        {!l.convertido && !l.bot_pausado && !l.opt_out && (
                          <span className="bg-sky-500/10 text-sky-400 text-[10px] uppercase tracking-wider px-2 py-0.5 rounded font-bold">
                            Ativo
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-3 px-6">
                      <div className="flex items-center gap-2 text-xs text-slate-300">
                        <Bot className="w-3.5 h-3.5 text-cigana-purple" />
                        {l.node_atual || 'Início'}
                      </div>
                    </td>
                    <td className="py-3 px-6">
                      {l.ultima_em ? (
                        <div>
                          <div className="text-xs text-slate-300">
                            {new Date(l.ultima_em).toLocaleDateString()} às {new Date(l.ultima_em).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </div>
                          <div className="text-[10px] text-slate-500 line-clamp-1 max-w-[200px]">
                            {l.ultima_msg}
                          </div>
                        </div>
                      ) : (
                        <span className="text-xs text-slate-500">Sem interações</span>
                      )}
                    </td>
                    <td className="py-3 px-6 text-right">
                      <a href={`/inbox`} className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 rounded-lg text-xs font-semibold transition-colors">
                        <MessageSquare className="w-3.5 h-3.5" />
                        Chat
                      </a>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
