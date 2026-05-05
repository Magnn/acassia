import React, { useState, useEffect } from 'react';
import { 
  Receipt, 
  Search, 
  FileText, 
  Download, 
  CheckCircle, 
  Clock, 
  AlertCircle, 
  Plus,
  RefreshCw
} from 'lucide-react';
import api from '../api/client';
import { toast } from 'react-hot-toast';

interface NotaFiscal {
  id: number;
  tipo: string;
  numero: number | null;
  chave_acesso: string | null;
  valor_total: number;
  nome_cliente: string;
  cpf_cnpj: string;
  status: string;
  url_pdf: string | null;
  created_at: string;
}

export default function Fiscal() {
  const [notas, setNotas] = useState<NotaFiscal[]>([]);
  const [loading, setLoading] = useState(true);
  const [isEmitting, setIsEmitting] = useState(false);
  const [showModal, setShowModal] = useState(false);
  
  // Form state
  const [valor, setValor] = useState('');
  const [documento, setDocumento] = useState('');
  const [nome, setNome] = useState('');
  const [descricao, setDescricao] = useState('');
  const [tipo, setTipo] = useState('NFSe');

  const fetchNotas = async () => {
    setLoading(true);
    try {
      const { data } = await api.get('/saas/fiscal/notas');
      if (data.ok) {
        setNotas(data.data);
      }
    } catch (error) {
      toast.error('Erro ao buscar notas fiscais');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNotas();
  }, []);

  const handleEmitir = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsEmitting(true);
    try {
      const payload = {
        valor: parseFloat(valor),
        documento,
        nome,
        descricao,
        tipo
      };
      const { data } = await api.post('/saas/fiscal/emitir', payload);
      if (data.ok) {
        toast.success('Nota emitida com sucesso!');
        setShowModal(false);
        fetchNotas();
      }
    } catch (error: any) {
      toast.error(error.response?.data?.error || 'Erro ao emitir nota');
    } finally {
      setIsEmitting(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case 'autorizada': return <CheckCircle className="w-5 h-5 text-emerald-400" />;
      case 'processando': return <Clock className="w-5 h-5 text-yellow-400" />;
      case 'rejeitada': return <AlertCircle className="w-5 h-5 text-red-400" />;
      default: return <FileText className="w-5 h-5 text-zinc-400" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'autorizada': return 'bg-emerald-400/10 text-emerald-400 border-emerald-400/20';
      case 'processando': return 'bg-yellow-400/10 text-yellow-400 border-yellow-400/20';
      case 'rejeitada': return 'bg-red-400/10 text-red-400 border-red-400/20';
      default: return 'bg-zinc-800 text-zinc-400 border-zinc-700';
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 animate-in fade-in duration-500">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-zinc-900/50 p-6 rounded-2xl border border-white/5">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center gap-3">
            <Receipt className="w-8 h-8 text-indigo-400" />
            Central Fiscal
          </h1>
          <p className="text-zinc-400 mt-2 text-lg">
            Emissão e gestão de Notas Fiscais (NFe, NFSe, NFCe)
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button 
            onClick={fetchNotas}
            className="p-3 text-zinc-400 hover:text-white hover:bg-white/5 rounded-xl transition-all"
          >
            <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <button 
            onClick={() => setShowModal(true)}
            className="flex items-center gap-2 bg-indigo-500 hover:bg-indigo-600 text-white px-6 py-3 rounded-xl font-medium transition-all shadow-lg shadow-indigo-500/20 hover:shadow-indigo-500/40"
          >
            <Plus className="w-5 h-5" />
            Emitir Nova Nota
          </button>
        </div>
      </div>

      {/* Tabela de Notas */}
      <div className="bg-zinc-900/50 rounded-2xl border border-white/5 overflow-hidden">
        <div className="p-6 border-b border-white/5 flex flex-col sm:flex-row justify-between items-center gap-4">
          <h2 className="text-xl font-semibold text-white">Histórico de Emissões</h2>
          
          <div className="relative w-full sm:w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
            <input 
              type="text" 
              placeholder="Buscar por cliente ou CPF/CNPJ..."
              className="w-full bg-black/40 border border-white/10 rounded-lg pl-10 pr-4 py-2 text-sm text-white focus:outline-none focus:border-indigo-500/50 transition-colors"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-black/20 text-xs uppercase tracking-wider text-zinc-500">
                <th className="p-4 font-medium">Status</th>
                <th className="p-4 font-medium">Documento</th>
                <th className="p-4 font-medium">Cliente</th>
                <th className="p-4 font-medium">Valor</th>
                <th className="p-4 font-medium">Chave / Número</th>
                <th className="p-4 font-medium">Data</th>
                <th className="p-4 font-medium text-right">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {loading && notas.length === 0 ? (
                <tr>
                  <td colSpan={7} className="p-8 text-center text-zinc-500">
                    Carregando notas fiscais...
                  </td>
                </tr>
              ) : notas.length === 0 ? (
                <tr>
                  <td colSpan={7} className="p-12 text-center text-zinc-500">
                    <Receipt className="w-12 h-12 mx-auto text-zinc-700 mb-4" />
                    <p className="text-lg">Nenhuma nota fiscal emitida ainda.</p>
                  </td>
                </tr>
              ) : (
                notas.map((nota) => (
                  <tr key={nota.id} className="hover:bg-white/[0.02] transition-colors">
                    <td className="p-4">
                      <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${getStatusColor(nota.status)}`}>
                        {getStatusIcon(nota.status)}
                        <span className="capitalize">{nota.status}</span>
                      </div>
                    </td>
                    <td className="p-4">
                      <span className="inline-block bg-zinc-800 text-zinc-300 text-xs px-2 py-1 rounded font-mono">
                        {nota.tipo}
                      </span>
                    </td>
                    <td className="p-4">
                      <div className="font-medium text-white">{nota.nome_cliente || 'N/A'}</div>
                      <div className="text-xs text-zinc-500">{nota.cpf_cnpj || '---'}</div>
                    </td>
                    <td className="p-4 font-medium text-emerald-400">
                      {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(nota.valor_total)}
                    </td>
                    <td className="p-4">
                      {nota.numero ? (
                        <div>
                          <div className="text-sm text-zinc-300">Nº {nota.numero}</div>
                          <div className="text-xs text-zinc-500 font-mono truncate max-w-[120px]" title={nota.chave_acesso || ''}>
                            {nota.chave_acesso || '---'}
                          </div>
                        </div>
                      ) : (
                        <span className="text-zinc-600 text-sm">Aguardando...</span>
                      )}
                    </td>
                    <td className="p-4 text-sm text-zinc-400">
                      {new Date(nota.created_at).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}
                    </td>
                    <td className="p-4 text-right">
                      {nota.url_pdf ? (
                        <a 
                          href={nota.url_pdf} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-2 px-3 py-1.5 bg-indigo-500/10 text-indigo-400 hover:bg-indigo-500/20 rounded-lg text-sm font-medium transition-colors"
                        >
                          <Download className="w-4 h-4" />
                          DANFE
                        </a>
                      ) : (
                        <button disabled className="inline-flex items-center gap-2 px-3 py-1.5 bg-zinc-800 text-zinc-600 rounded-lg text-sm font-medium cursor-not-allowed">
                          Indisponível
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal de Emissão Manual */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="bg-zinc-900 border border-white/10 rounded-2xl w-full max-w-lg overflow-hidden shadow-2xl animate-in zoom-in-95 duration-200">
            <div className="p-6 border-b border-white/5 flex justify-between items-center">
              <h3 className="text-xl font-semibold text-white flex items-center gap-2">
                <Receipt className="w-5 h-5 text-indigo-400" />
                Emitir Nota Fiscal
              </h3>
              <button 
                onClick={() => setShowModal(false)}
                className="text-zinc-500 hover:text-white transition-colors"
              >
                ✕
              </button>
            </div>
            
            <form onSubmit={handleEmitir} className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-sm font-medium text-zinc-400">Tipo de Documento</label>
                  <select 
                    value={tipo}
                    onChange={e => setTipo(e.target.value)}
                    className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:border-indigo-500 transition-colors"
                  >
                    <option value="NFSe">NFS-e (Serviço)</option>
                    <option value="NFCe">NFC-e (Consumidor)</option>
                    <option value="NFe">NF-e (Produto)</option>
                  </select>
                </div>
                
                <div className="space-y-1.5">
                  <label className="text-sm font-medium text-zinc-400">Valor Total (R$)</label>
                  <input 
                    type="number" 
                    step="0.01"
                    required
                    value={valor}
                    onChange={e => setValor(e.target.value)}
                    placeholder="0.00"
                    className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:border-indigo-500 transition-colors"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-sm font-medium text-zinc-400">CPF ou CNPJ do Cliente</label>
                <input 
                  type="text" 
                  required
                  value={documento}
                  onChange={e => setDocumento(e.target.value)}
                  placeholder="000.000.000-00"
                  className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:border-indigo-500 transition-colors font-mono"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-sm font-medium text-zinc-400">Nome ou Razão Social</label>
                <input 
                  type="text" 
                  required
                  value={nome}
                  onChange={e => setNome(e.target.value)}
                  placeholder="Nome do Cliente"
                  className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:border-indigo-500 transition-colors"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-sm font-medium text-zinc-400">Descrição do Serviço / Produto</label>
                <textarea 
                  required
                  value={descricao}
                  onChange={e => setDescricao(e.target.value)}
                  placeholder="Ex: Consulta Terapêutica Online (40 min)"
                  rows={3}
                  className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:border-indigo-500 transition-colors resize-none"
                />
              </div>

              <div className="pt-4 flex gap-3">
                <button 
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="flex-1 bg-zinc-800 hover:bg-zinc-700 text-white px-4 py-3 rounded-xl font-medium transition-colors"
                >
                  Cancelar
                </button>
                <button 
                  type="submit"
                  disabled={isEmitting}
                  className="flex-1 bg-indigo-500 hover:bg-indigo-600 text-white px-4 py-3 rounded-xl font-medium transition-all shadow-lg shadow-indigo-500/20 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {isEmitting ? (
                    <><RefreshCw className="w-5 h-5 animate-spin" /> Emitindo...</>
                  ) : (
                    <><CheckCircle className="w-5 h-5" /> Confirmar Emissão</>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
