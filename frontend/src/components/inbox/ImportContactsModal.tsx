import React, { useState, useRef, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Upload,
  FileText,
  CheckCircle2,
  AlertCircle,
  Clock,
  RefreshCw,
  X,
  ArrowRight,
  Download,
  History,
  Smartphone,
  Plus,
  Trash2,
  ChevronRight,
  Info,
  Layers,
} from 'lucide-react';
import { contactsImportApi, ContactImportItem, sequencesApi } from '../../api/saas';
import { toast } from '../../lib/toast';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

type TabType = 'csv' | 'whatsapp' | 'history';

interface ParsedRow {
  [key: string]: string;
}

export default function ImportContactsModal({ isOpen, onClose, onSuccess }: Props) {
  const qc = useQueryClient();
  const [activeTab, setActiveTab] = useState<TabType>('csv');

  // CSV Import State
  const [file, setFile] = useState<File | null>(null);
  const [fileName, setFileName] = useState<string>('');
  const [csvHeaders, setCsvHeaders] = useState<string[]>([]);
  const [csvRows, setCsvRows] = useState<ParsedRow[]>([]);
  const [mapping, setMapping] = useState<{ phone: string; name: string; email: string }>({
    phone: '',
    name: '',
    email: '',
  });
  const [tagInput, setTagInput] = useState('');
  const [tags, setTags] = useState<string[]>([]);
  const [selectedSequenceId, setSelectedSequenceId] = useState<number | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // History Error Modal State
  const [selectedErrorLog, setSelectedErrorLog] = useState<Array<{ row?: number; reason: string }> | null>(null);

  // Fetch Sequences for Auto-enrollment
  const { data: seqData } = useQuery({
    queryKey: ['sequences-list-for-import'],
    queryFn: sequencesApi.list,
    enabled: isOpen && activeTab === 'csv',
  });

  // Fetch Import History
  const { data: historyData, isLoading: isLoadingHistory, refetch: refetchHistory } = useQuery({
    queryKey: ['contacts-import-history'],
    queryFn: contactsImportApi.list,
    enabled: isOpen && activeTab === 'history',
  });

  // Process CSV Import Mutation
  const importMutation = useMutation({
    mutationFn: contactsImportApi.processImport,
    onSuccess: (res) => {
      toast.success(res.message || 'Importação realizada com sucesso!');
      qc.invalidateQueries({ queryKey: ['leads-list'] });
      qc.invalidateQueries({ queryKey: ['contacts-import-history'] });
      onSuccess?.();
      handleResetCsv();
      setActiveTab('history');
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.error || err.message || 'Erro ao processar importação');
    },
  });

  // Sync WhatsApp Mutation
  const syncMutation = useMutation({
    mutationFn: contactsImportApi.syncWhatsApp,
    onSuccess: (res) => {
      toast.success(res.message || 'Contatos do WhatsApp sincronizados com sucesso!');
      qc.invalidateQueries({ queryKey: ['leads-list'] });
      qc.invalidateQueries({ queryKey: ['contacts-import-history'] });
      onSuccess?.();
      setActiveTab('history');
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.error || err.message || 'Erro ao sincronizar WhatsApp');
    },
  });

  // CSV Parsing helper (handles commas, semicolons, quotes)
  const parseCsvText = (text: string) => {
    const lines = text
      .split(/\r\n|\n|\r/)
      .map((l) => l.trim())
      .filter(Boolean);
    if (lines.length === 0) return { headers: [], rows: [] };

    // Auto-detect delimiter (, or ;)
    const firstLine = lines[0];
    const commaCount = (firstLine.match(/,/g) || []).length;
    const semiCount = (firstLine.match(/;/g) || []).length;
    const delimiter = semiCount > commaCount ? ';' : ',';

    const parseLine = (line: string): string[] => {
      const result: string[] = [];
      let current = '';
      let inQuotes = false;
      for (let i = 0; i < line.length; i++) {
        const char = line[i];
        if (char === '"') {
          inQuotes = !inQuotes;
        } else if (char === delimiter && !inQuotes) {
          result.push(current.trim().replace(/^"|"$/g, ''));
          current = '';
        } else {
          current += char;
        }
      }
      result.push(current.trim().replace(/^"|"$/g, ''));
      return result;
    };

    const rawHeaders = parseLine(lines[0]);
    const headers = rawHeaders.filter((h) => h.length > 0);

    const rows: ParsedRow[] = [];
    for (let i = 1; i < lines.length; i++) {
      const values = parseLine(lines[i]);
      if (values.length === 0 || (values.length === 1 && values[0] === '')) continue;
      const row: ParsedRow = {};
      headers.forEach((header, idx) => {
        row[header] = values[idx] || '';
      });
      rows.push(row);
    }

    return { headers, rows };
  };

  const handleFile = (selectedFile: File) => {
    if (!selectedFile) return;
    setFile(selectedFile);
    setFileName(selectedFile.name);

    const reader = new FileReader();
    reader.onload = (e) => {
      const content = (e.target?.result as string) || '';
      const { headers, rows } = parseCsvText(content);
      setCsvHeaders(headers);
      setCsvRows(rows);

      // Auto-detect mappings
      let autoPhone = '';
      let autoName = '';
      let autoEmail = '';

      headers.forEach((h) => {
        const lower = h.toLowerCase();
        if (!autoPhone && (lower.includes('tel') || lower.includes('cel') || lower.includes('zap') || lower.includes('phone') || lower.includes('whats'))) {
          autoPhone = h;
        }
        if (!autoName && (lower.includes('nome') || lower.includes('name') || lower.includes('cliente') || lower.includes('contato'))) {
          autoName = h;
        }
        if (!autoEmail && (lower.includes('mail') || lower.includes('email') || lower.includes('e-mail'))) {
          autoEmail = h;
        }
      });

      setMapping({
        phone: autoPhone || headers[0] || '',
        name: autoName,
        email: autoEmail,
      });
    };
    reader.readAsText(selectedFile);
  };

  const handleResetCsv = () => {
    setFile(null);
    setFileName('');
    setCsvHeaders([]);
    setCsvRows([]);
    setMapping({ phone: '', name: '', email: '' });
    setTags([]);
    setSelectedSequenceId(null);
  };

  const handleAddTag = () => {
    const val = tagInput.trim().toLowerCase();
    if (val && !tags.includes(val)) {
      setTags([...tags, val]);
      setTagInput('');
    }
  };

  const handleRemoveTag = (t: string) => {
    setTags(tags.filter((x) => x !== t));
  };

  const handleStartImport = () => {
    if (!file || csvRows.length === 0) {
      toast.error('Selecione um arquivo CSV com contatos.');
      return;
    }
    if (!mapping.phone) {
      toast.error('Selecione qual coluna do CSV corresponde ao Telefone / WhatsApp.');
      return;
    }

    const payloadMapping: Record<string, string> = {
      [mapping.phone]: 'telefone',
    };
    if (mapping.name) payloadMapping[mapping.name] = 'nome';
    if (mapping.email) payloadMapping[mapping.email] = 'email';

    importMutation.mutate({
      name: fileName || 'contatos.csv',
      rows: csvRows,
      mapping: payloadMapping,
      assigned_tags: tags,
      enroll_sequence_id: selectedSequenceId,
    });
  };

  const downloadSampleTemplate = () => {
    const csvContent = 'Nome Completo,Telefone com DDD,Email\nMaria Madalena,11988887777,maria@exemplo.com\nJoão Batista,21977776666,joao@exemplo.com\nAna Clara,31999998888,ana@exemplo.com';
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', 'modelo_importacao_contatos.csv');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fade-in">
      <div className="bg-zinc-950 border border-zinc-800 rounded-2xl w-full max-w-3xl shadow-2xl flex flex-col max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-800/80 bg-zinc-900/40">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-purple-500/10 border border-purple-500/20 text-purple-400">
              <Upload className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white">Importar Contatos & Histórico</h2>
              <p className="text-xs text-zinc-400">
                Padrão ChatbotX: Adicione novos contatos em massa, mapeie colunas e sincronize conversas
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-zinc-400 hover:text-white hover:bg-zinc-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex items-center border-b border-zinc-800/80 px-6 bg-zinc-900/20 gap-2">
          <button
            onClick={() => setActiveTab('csv')}
            className={`flex items-center gap-2 py-3 px-4 text-xs font-semibold border-b-2 transition-colors ${
              activeTab === 'csv'
                ? 'border-purple-500 text-purple-400 font-bold'
                : 'border-transparent text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <FileText className="w-4 h-4" />
            Importar CSV
          </button>
          <button
            onClick={() => setActiveTab('whatsapp')}
            className={`flex items-center gap-2 py-3 px-4 text-xs font-semibold border-b-2 transition-colors ${
              activeTab === 'whatsapp'
                ? 'border-purple-500 text-purple-400 font-bold'
                : 'border-transparent text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <Smartphone className="w-4 h-4" />
            Sincronizar WhatsApp
          </button>
          <button
            onClick={() => setActiveTab('history')}
            className={`flex items-center gap-2 py-3 px-4 text-xs font-semibold border-b-2 transition-colors ${
              activeTab === 'history'
                ? 'border-purple-500 text-purple-400 font-bold'
                : 'border-transparent text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <History className="w-4 h-4" />
            Histórico de Importações
          </button>
        </div>

        {/* Modal Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar">
          {/* TAB 1: CSV IMPORT */}
          {activeTab === 'csv' && (
            <>
              {/* Dropzone if no file selected */}
              {!file ? (
                <div className="space-y-4">
                  <div className="flex justify-end">
                    <button
                      onClick={downloadSampleTemplate}
                      className="inline-flex items-center gap-1.5 text-xs text-purple-400 hover:text-purple-300 transition-colors font-medium"
                    >
                      <Download className="w-3.5 h-3.5" />
                      Baixar Modelo CSV Exemplo
                    </button>
                  </div>

                  <div
                    onDragOver={(e) => {
                      e.preventDefault();
                      setDragOver(true);
                    }}
                    onDragLeave={() => setDragOver(false)}
                    onDrop={(e) => {
                      e.preventDefault();
                      setDragOver(false);
                      if (e.dataTransfer.files?.[0]) {
                        handleFile(e.dataTransfer.files[0]);
                      }
                    }}
                    onClick={() => fileInputRef.current?.click()}
                    className={`border-2 border-dashed rounded-2xl p-10 flex flex-col items-center justify-center text-center cursor-pointer transition-all ${
                      dragOver
                        ? 'border-purple-500 bg-purple-500/10'
                        : 'border-zinc-800 hover:border-zinc-700 bg-zinc-900/30 hover:bg-zinc-900/50'
                    }`}
                  >
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".csv,text/csv"
                      className="hidden"
                      onChange={(e) => {
                        if (e.target.files?.[0]) handleFile(e.target.files[0]);
                      }}
                    />
                    <div className="p-3.5 rounded-2xl bg-zinc-800 text-zinc-300 mb-3 shadow-inner">
                      <Upload className="w-6 h-6 text-purple-400" />
                    </div>
                    <p className="text-sm font-semibold text-white">
                      Arraste e solte o arquivo CSV aqui ou clique para selecionar
                    </p>
                    <p className="text-xs text-zinc-400 mt-1 max-w-sm">
                      Suporta arquivos CSV com separador vírgula ou ponto e vírgula contendo nome, telefone e email.
                    </p>
                  </div>
                </div>
              ) : (
                /* File Selected & Mapping Step */
                <div className="space-y-6">
                  {/* File Info Banner */}
                  <div className="flex items-center justify-between p-3.5 rounded-xl bg-zinc-900 border border-zinc-800">
                    <div className="flex items-center gap-3">
                      <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
                        <CheckCircle2 className="w-5 h-5" />
                      </div>
                      <div>
                        <div className="text-sm font-semibold text-white">{fileName}</div>
                        <div className="text-xs text-zinc-400">
                          {csvRows.length} linhas detectadas • {csvHeaders.length} colunas
                        </div>
                      </div>
                    </div>
                    <button
                      onClick={handleResetCsv}
                      className="text-xs text-zinc-400 hover:text-red-400 transition-colors p-1.5"
                    >
                      Trocar arquivo
                    </button>
                  </div>

                  {/* Preview of first 3 rows */}
                  <div className="space-y-2">
                    <div className="text-xs font-semibold text-zinc-300 uppercase tracking-wider">
                      Prévia dos Dados (Primeiras 3 Linhas)
                    </div>
                    <div className="overflow-x-auto border border-zinc-800 rounded-xl bg-zinc-900/40">
                      <table className="w-full text-left text-xs text-zinc-300">
                        <thead className="bg-zinc-900/80 border-b border-zinc-800 text-zinc-400 font-semibold">
                          <tr>
                            {csvHeaders.map((h, i) => (
                              <th key={i} className="px-3 py-2">
                                {h}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-zinc-800/60">
                          {csvRows.slice(0, 3).map((r, i) => (
                            <tr key={i} className="hover:bg-zinc-800/30">
                              {csvHeaders.map((h, j) => (
                                <td key={j} className="px-3 py-2 text-zinc-300 max-w-[180px] truncate">
                                  {r[h] || '—'}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {/* Visual Column Mapping (ChatbotX De-Para) */}
                  <div className="space-y-3">
                    <div className="text-xs font-semibold text-zinc-300 uppercase tracking-wider flex items-center gap-1.5">
                      <ArrowRight className="w-3.5 h-3.5 text-purple-400" />
                      Mapeamento de Colunas (De-Para)
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                      {/* Telefone (Obrigatório) */}
                      <div className="p-3 rounded-xl bg-zinc-900 border border-zinc-800 space-y-1.5">
                        <label className="text-xs font-bold text-white flex items-center justify-between">
                          <span>Telefone / WhatsApp *</span>
                          <span className="text-[10px] text-red-400 font-normal">Obrigatório</span>
                        </label>
                        <select
                          value={mapping.phone}
                          onChange={(e) => setMapping({ ...mapping, phone: e.target.value })}
                          className="w-full text-xs rounded-lg border border-zinc-700 bg-zinc-950 p-2 text-white focus:outline-none focus:border-purple-500"
                        >
                          <option value="">Selecione a coluna...</option>
                          {csvHeaders.map((h) => (
                            <option key={h} value={h}>
                              Coluna: {h}
                            </option>
                          ))}
                        </select>
                      </div>

                      {/* Nome (Opcional) */}
                      <div className="p-3 rounded-xl bg-zinc-900 border border-zinc-800 space-y-1.5">
                        <label className="text-xs font-bold text-white">Nome do Contato</label>
                        <select
                          value={mapping.name}
                          onChange={(e) => setMapping({ ...mapping, name: e.target.value })}
                          className="w-full text-xs rounded-lg border border-zinc-700 bg-zinc-950 p-2 text-white focus:outline-none focus:border-purple-500"
                        >
                          <option value="">Nenhum (Ignorar)</option>
                          {csvHeaders.map((h) => (
                            <option key={h} value={h}>
                              Coluna: {h}
                            </option>
                          ))}
                        </select>
                      </div>

                      {/* Email (Opcional) */}
                      <div className="p-3 rounded-xl bg-zinc-900 border border-zinc-800 space-y-1.5">
                        <label className="text-xs font-bold text-white">Email</label>
                        <select
                          value={mapping.email}
                          onChange={(e) => setMapping({ ...mapping, email: e.target.value })}
                          className="w-full text-xs rounded-lg border border-zinc-700 bg-zinc-950 p-2 text-white focus:outline-none focus:border-purple-500"
                        >
                          <option value="">Nenhum (Ignorar)</option>
                          {csvHeaders.map((h) => (
                            <option key={h} value={h}>
                              Coluna: {h}
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>
                  </div>

                  {/* Advanced Actions: Tags & Auto-Enroll in Sequence */}
                  <div className="p-4 rounded-xl bg-zinc-900/60 border border-zinc-800 space-y-4">
                    <div className="text-xs font-semibold text-zinc-300 uppercase tracking-wider flex items-center gap-1.5">
                      <Layers className="w-3.5 h-3.5 text-purple-400" />
                      Ações Pós-Importação
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {/* Atribuir Tags */}
                      <div className="space-y-2">
                        <label className="text-xs font-medium text-zinc-300">
                          Atribuir Tags aos Contatos Importados
                        </label>
                        <div className="flex gap-2">
                          <input
                            type="text"
                            placeholder="Ex: vip, lead-evento, import-abril"
                            value={tagInput}
                            onChange={(e) => setTagInput(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') {
                                e.preventDefault();
                                handleAddTag();
                              }
                            }}
                            className="flex-1 text-xs rounded-lg border border-zinc-700 bg-zinc-950 p-2 text-white focus:outline-none focus:border-purple-500"
                          />
                          <button
                            type="button"
                            onClick={handleAddTag}
                            className="px-3 py-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-xs font-semibold text-white transition-colors"
                          >
                            Adicionar
                          </button>
                        </div>
                        {tags.length > 0 && (
                          <div className="flex flex-wrap gap-1.5 pt-1">
                            {tags.map((t) => (
                              <span
                                key={t}
                                className="inline-flex items-center gap-1 text-[11px] font-medium bg-purple-500/20 text-purple-300 border border-purple-500/30 px-2 py-0.5 rounded-md"
                              >
                                #{t}
                                <button
                                  type="button"
                                  onClick={() => handleRemoveTag(t)}
                                  className="hover:text-white"
                                >
                                  ×
                                </button>
                              </span>
                            ))}
                          </div>
                        )}
                      </div>

                      {/* Auto-enroll in Sequence */}
                      <div className="space-y-2">
                        <label className="text-xs font-medium text-zinc-300">
                          Inscrever em Sequência (Drip Campaign)
                        </label>
                        <select
                          value={selectedSequenceId || ''}
                          onChange={(e) => setSelectedSequenceId(e.target.value ? Number(e.target.value) : null)}
                          className="w-full text-xs rounded-lg border border-zinc-700 bg-zinc-950 p-2 text-white focus:outline-none focus:border-purple-500"
                        >
                          <option value="">Não inscrever em nenhuma sequência</option>
                          {(seqData?.sequences || []).map((seq) => (
                            <option key={seq.id} value={seq.id}>
                              {seq.name} ({seq.messages} passos)
                            </option>
                          ))}
                        </select>
                        <p className="text-[11px] text-zinc-500">
                          Os contatos importados iniciarão imediatamente o passo 1 da régua configurada.
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}

          {/* TAB 2: WHATSAPP SYNC */}
          {activeTab === 'whatsapp' && (
            <div className="p-8 border border-zinc-800 rounded-2xl bg-zinc-900/30 text-center space-y-5">
              <div className="w-14 h-14 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center mx-auto">
                <Smartphone className="w-7 h-7" />
              </div>
              <div className="max-w-md mx-auto space-y-2">
                <h3 className="text-base font-bold text-white">Sincronizar Contatos e Histórico do WhatsApp</h3>
                <p className="text-xs text-zinc-400 leading-relaxed">
                  Sincroniza automaticamente contatos e mensagens recebidas via WhatsApp nos últimos meses.
                  As conversas existentes serão catalogadas e indexadas no CRM para nutrição imediata.
                </p>
              </div>

              <div className="pt-2">
                <button
                  type="button"
                  disabled={syncMutation.isPending}
                  onClick={() => syncMutation.mutate()}
                  className="px-6 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-bold shadow-lg shadow-emerald-600/20 transition-all inline-flex items-center gap-2"
                >
                  <RefreshCw className={`w-4 h-4 ${syncMutation.isPending ? 'animate-spin' : ''}`} />
                  {syncMutation.isPending ? 'Sincronizando Conversas...' : 'Iniciar Sincronização Agora'}
                </button>
              </div>
            </div>
          )}

          {/* TAB 3: IMPORT HISTORY TABLE */}
          {activeTab === 'history' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-zinc-300 uppercase tracking-wider">
                  Execuções Anteriores ({historyData?.imports?.length || 0})
                </span>
                <button
                  onClick={() => refetchHistory()}
                  className="p-1.5 rounded-lg border border-zinc-800 text-zinc-400 hover:text-white transition-colors"
                  title="Atualizar lista"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${isLoadingHistory ? 'animate-spin' : ''}`} />
                </button>
              </div>

              {isLoadingHistory ? (
                <div className="py-12 text-center text-xs text-zinc-500">Carregando histórico…</div>
              ) : (historyData?.imports || []).length === 0 ? (
                <div className="py-12 text-center text-xs text-zinc-500 border border-dashed border-zinc-800 rounded-xl">
                  Nenhuma importação realizada ainda.
                </div>
              ) : (
                <div className="border border-zinc-800 rounded-xl overflow-hidden bg-zinc-900/30">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-zinc-900 border-b border-zinc-800 text-zinc-400 font-semibold">
                      <tr>
                        <th className="px-4 py-3">Arquivo / Origem</th>
                        <th className="px-4 py-3">Status</th>
                        <th className="px-4 py-3 text-center">Total</th>
                        <th className="px-4 py-3 text-center">Sucesso</th>
                        <th className="px-4 py-3 text-center">Falhas</th>
                        <th className="px-4 py-3">Data</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-800/60 text-zinc-300">
                      {(historyData?.imports || []).map((item: ContactImportItem) => (
                        <tr key={item.id} className="hover:bg-zinc-800/20">
                          <td className="px-4 py-3 font-medium text-white max-w-[200px] truncate">
                            {item.name}
                          </td>
                          <td className="px-4 py-3">
                            <span
                              className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold ${
                                item.status === 'completed'
                                  ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                                  : item.status === 'completed_with_errors'
                                  ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                                  : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                              }`}
                            >
                              {item.status === 'completed'
                                ? 'Concluído'
                                : item.status === 'completed_with_errors'
                                ? 'Com Avisos'
                                : 'Falhou'}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-center tabular-nums text-zinc-400">
                            {item.total_rows}
                          </td>
                          <td className="px-4 py-3 text-center tabular-nums font-semibold text-emerald-400">
                            {item.success_rows}
                          </td>
                          <td className="px-4 py-3 text-center tabular-nums">
                            {item.failed_rows > 0 ? (
                              <button
                                onClick={() => setSelectedErrorLog(item.error_log || [])}
                                className="text-red-400 hover:text-red-300 underline font-semibold"
                                title="Ver detalhes dos erros"
                              >
                                {item.failed_rows} erros
                              </button>
                            ) : (
                              <span className="text-zinc-600">0</span>
                            )}
                          </td>
                          <td className="px-4 py-3 text-zinc-400">
                            {item.created_at ? new Date(item.created_at).toLocaleString('pt-BR') : '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-zinc-800/80 bg-zinc-900/40">
          <div className="text-xs text-zinc-500">
            {activeTab === 'csv' && file && `${csvRows.length} contatos prontos para importar`}
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-xl border border-zinc-700 hover:bg-zinc-800 text-xs font-semibold text-zinc-300 transition-colors"
            >
              Fechar
            </button>
            {activeTab === 'csv' && file && (
              <button
                type="button"
                disabled={importMutation.isPending || !mapping.phone}
                onClick={handleStartImport}
                className="px-5 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white text-xs font-bold shadow-lg shadow-purple-600/20 transition-all flex items-center gap-2"
              >
                {importMutation.isPending ? 'Processando Importação...' : 'Confirmar e Importar'}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Error Log Modal */}
      {selectedErrorLog && (
        <div className="fixed inset-0 z-60 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-lg shadow-2xl p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
              <h4 className="text-sm font-bold text-white flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-red-400" />
                Relatório de Linhas Inválidas
              </h4>
              <button
                onClick={() => setSelectedErrorLog(null)}
                className="p-1 text-zinc-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="max-h-64 overflow-y-auto space-y-2 pr-1 custom-scrollbar">
              {selectedErrorLog.map((err, i) => (
                <div key={i} className="p-2.5 rounded-lg bg-zinc-950 border border-zinc-800/80 text-xs">
                  <span className="font-bold text-red-400">Linha {err.row || i + 1}: </span>
                  <span className="text-zinc-300">{err.reason}</span>
                </div>
              ))}
            </div>
            <div className="flex justify-end pt-2">
              <button
                onClick={() => setSelectedErrorLog(null)}
                className="px-4 py-1.5 rounded-lg bg-zinc-800 text-xs text-white font-medium hover:bg-zinc-700"
              >
                Fechar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
