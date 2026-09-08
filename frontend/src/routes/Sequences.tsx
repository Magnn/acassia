import React, { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  GitBranch,
  Plus,
  Play,
  Search,
  Users,
  Layers,
  Clock,
  Calendar,
  CheckCircle2,
  XCircle,
  MoreVertical,
  Edit2,
  Trash2,
  ChevronDown,
  ChevronRight,
  ArrowLeft,
  Eye,
  MousePointer,
  Send,
  AlertCircle,
  Sparkles,
  Workflow,
  FileText,
  UserPlus,
  UserMinus,
  RefreshCw,
} from 'lucide-react';
import { sequencesApi, SequenceItem, SequenceStepItem, EnrolledContactItem } from '../api/saas';
import { blueprintsApi } from '../api/blueprints';
import { inboxApi } from '../api/inbox';
import { toast } from '../lib/toast';

const DAYS_OF_WEEK = [
  { id: 'monday', label: 'Seg' },
  { id: 'tuesday', label: 'Ter' },
  { id: 'wednesday', label: 'Qua' },
  { id: 'thursday', label: 'Qui' },
  { id: 'friday', label: 'Sex' },
  { id: 'saturday', label: 'Sáb' },
  { id: 'sunday', label: 'Dom' },
];

export default function Sequences() {
  const queryClient = useQueryClient();
  const [selectedSequenceId, setSelectedSequenceId] = useState<number | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  
  // Modais
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [sequenceToRename, setSequenceToRename] = useState<SequenceItem | null>(null);
  const [sequenceToDelete, setSequenceToDelete] = useState<SequenceItem | null>(null);

  // Queries
  const { data: sequencesData, isLoading: isLoadingList } = useQuery({
    queryKey: ['saas-sequences'],
    queryFn: () => sequencesApi.list(),
  });

  const { data: activeSequenceData, isLoading: isLoadingDetail } = useQuery({
    queryKey: ['saas-sequence', selectedSequenceId],
    queryFn: () => sequencesApi.get(selectedSequenceId!),
    enabled: !!selectedSequenceId,
  });

  const { data: blueprintsData } = useQuery({
    queryKey: ['blueprints-list'],
    queryFn: () => blueprintsApi.list(),
  });

  const sequences: SequenceItem[] = sequencesData?.sequences || [];
  const activeSequence: SequenceItem | undefined = activeSequenceData?.sequence;
  const blueprints = blueprintsData || [];

  // Filtragem de lista
  const filteredSequences = useMemo(() => {
    if (!searchTerm.trim()) return sequences;
    const term = searchTerm.toLowerCase();
    return sequences.filter((s: SequenceItem) => s.name.toLowerCase().includes(term));
  }, [sequences, searchTerm]);

  // Executar disparos devidos
  const processDueMutation = useMutation({
    mutationFn: () => sequencesApi.processDue(),
    onSuccess: (res) => {
      toast.success(`${res.processed} disparos processados.`);
      queryClient.invalidateQueries({ queryKey: ['saas-sequence', selectedSequenceId] });
    },
    onError: () => toast.error('Erro ao processar disparos devidos.'),
  });

  // Toggle status ativo da sequência
  const toggleActiveMutation = useMutation({
    mutationFn: ({ id, active }: { id: number; active: boolean }) =>
      sequencesApi.update(id, { active }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['saas-sequences'] });
      if (selectedSequenceId) {
        queryClient.invalidateQueries({ queryKey: ['saas-sequence', selectedSequenceId] });
      }
      toast.success('Status da sequência atualizado.');
    },
    onError: () => toast.error('Erro ao atualizar status.'),
  });

  if (selectedSequenceId && activeSequence) {
    return (
      <SequenceDetailView
        sequence={activeSequence}
        blueprints={blueprints}
        onBack={() => setSelectedSequenceId(null)}
        onProcessDue={() => processDueMutation.mutate()}
        isProcessingDue={processDueMutation.isPending}
      />
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6 text-zinc-100">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-zinc-800/80 pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-purple-500/10 border border-purple-500/20 text-purple-400">
              <GitBranch className="w-5 h-5" />
            </div>
            <h1 className="text-xl font-bold tracking-tight text-zinc-100">
              Sequências (Drip Campaigns)
            </h1>
            <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-purple-500/15 text-purple-300 border border-purple-500/30">
              ChatbotX Parity
            </span>
          </div>
          <p className="text-sm text-zinc-400 mt-1">
            Automatize réguas de nutrição multi-dias com delays programados, horários permitidos e métricas por passo.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={() => processDueMutation.mutate()}
            disabled={processDueMutation.isPending}
            className="flex items-center gap-2 px-3.5 py-2 text-xs font-medium rounded-lg bg-zinc-800/80 hover:bg-zinc-700 text-zinc-300 border border-zinc-700/60 transition"
          >
            <Play className={`w-3.5 h-3.5 text-emerald-400 ${processDueMutation.isPending ? 'animate-spin' : ''}`} />
            Executar Pendentes
          </button>
          <button
            onClick={() => setIsCreateOpen(true)}
            className="flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-lg bg-purple-600 hover:bg-purple-500 text-white shadow-lg shadow-purple-900/30 transition"
          >
            <Plus className="w-4 h-4" />
            Nova Sequência
          </button>
        </div>
      </div>

      {/* Toolbar / Search */}
      <div className="flex items-center justify-between gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
          <input
            type="text"
            placeholder="Buscar sequência pelo nome..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-4 py-2 bg-zinc-900/80 border border-zinc-800 rounded-lg text-sm text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-purple-500 transition"
          />
        </div>
      </div>

      {/* Table List */}
      <div className="bg-zinc-900/50 border border-zinc-800/80 rounded-xl overflow-hidden shadow-xl">
        {isLoadingList ? (
          <div className="py-20 text-center text-zinc-500 text-sm flex items-center justify-center gap-2">
            <RefreshCw className="w-4 h-4 animate-spin text-purple-400" />
            Carregando sequências...
          </div>
        ) : filteredSequences.length === 0 ? (
          <div className="py-20 text-center text-zinc-500 space-y-3">
            <Layers className="w-10 h-10 mx-auto text-zinc-600" />
            <p className="text-sm font-medium text-zinc-400">Nenhuma sequência encontrada</p>
            <p className="text-xs text-zinc-500 max-w-sm mx-auto">
              Crie réguas de acompanhamento automatizadas para engajar leads que entraram no funil.
            </p>
            <button
              onClick={() => setIsCreateOpen(true)}
              className="mt-2 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-purple-600/20 text-purple-300 border border-purple-500/30 text-xs font-semibold hover:bg-purple-600/30 transition"
            >
              <Plus className="w-3.5 h-3.5" />
              Criar primeira sequência
            </button>
          </div>
        ) : (
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-zinc-800/80 bg-zinc-950/40 text-[11px] font-semibold text-zinc-400 uppercase tracking-wider">
                <th className="py-3.5 px-4">Nome da Sequência</th>
                <th className="py-3.5 px-4 text-center">Status</th>
                <th className="py-3.5 px-4 text-center">Inscritos</th>
                <th className="py-3.5 px-4 text-center">Passos</th>
                <th className="py-3.5 px-4">Criada em</th>
                <th className="py-3.5 px-4 text-right">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/50 text-sm">
              {filteredSequences.map((seq: SequenceItem) => (
                <tr
                  key={seq.id}
                  className="hover:bg-zinc-800/30 transition cursor-pointer group"
                  onClick={() => setSelectedSequenceId(seq.id)}
                >
                  <td className="py-3.5 px-4 font-medium text-zinc-100 flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-zinc-800/80 text-zinc-400 group-hover:text-purple-400 transition">
                      <Workflow className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="group-hover:text-purple-300 transition font-semibold">
                        {seq.name}
                      </div>
                      {seq.folder_name && (
                        <span className="text-[11px] text-zinc-500">Pasta: {seq.folder_name}</span>
                      )}
                    </div>
                  </td>
                  <td className="py-3.5 px-4 text-center" onClick={(e) => e.stopPropagation()}>
                    <button
                      onClick={() => toggleActiveMutation.mutate({ id: seq.id, active: !seq.active })}
                      className={`px-2.5 py-1 rounded-full text-xs font-semibold border transition inline-flex items-center gap-1.5 ${
                        seq.active
                          ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                          : 'bg-zinc-800 text-zinc-400 border-zinc-700'
                      }`}
                    >
                      <span className={`w-1.5 h-1.5 rounded-full ${seq.active ? 'bg-emerald-400' : 'bg-zinc-500'}`} />
                      {seq.active ? 'Ativa' : 'Inativa'}
                    </button>
                  </td>
                  <td className="py-3.5 px-4 text-center">
                    <span className="inline-flex items-center gap-1 text-xs text-zinc-300 font-medium px-2 py-0.5 rounded bg-zinc-800/60 border border-zinc-700/50">
                      <Users className="w-3 h-3 text-zinc-400" />
                      {seq.subscribers}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 text-center">
                    <span className="inline-flex items-center gap-1 text-xs text-zinc-300 font-medium px-2 py-0.5 rounded bg-zinc-800/60 border border-zinc-700/50">
                      <Layers className="w-3 h-3 text-zinc-400" />
                      {seq.messages}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 text-xs text-zinc-400">
                    {seq.created_at ? new Date(seq.created_at).toLocaleDateString('pt-BR') : '—'}
                  </td>
                  <td className="py-3.5 px-4 text-right" onClick={(e) => e.stopPropagation()}>
                    <div className="inline-flex items-center gap-1">
                      <button
                        onClick={() => setSelectedSequenceId(seq.id)}
                        className="p-1.5 hover:bg-zinc-800 rounded-lg text-zinc-400 hover:text-zinc-200 transition"
                        title="Editar passos"
                      >
                        <Edit2 className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => setSequenceToRename(seq)}
                        className="p-1.5 hover:bg-zinc-800 rounded-lg text-zinc-400 hover:text-zinc-200 transition"
                        title="Renomear"
                      >
                        <FileText className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => setSequenceToDelete(seq)}
                        className="p-1.5 hover:bg-rose-500/20 rounded-lg text-zinc-400 hover:text-rose-400 transition"
                        title="Excluir"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Modal Criar Sequência */}
      {isCreateOpen && (
        <CreateSequenceModal
          onClose={() => setIsCreateOpen(false)}
          onCreated={(newSeq) => {
            setIsCreateOpen(false);
            queryClient.invalidateQueries({ queryKey: ['saas-sequences'] });
            setSelectedSequenceId(newSeq.id);
          }}
        />
      )}

      {/* Modal Renomear Sequência */}
      {sequenceToRename && (
        <RenameSequenceModal
          sequence={sequenceToRename}
          onClose={() => setSequenceToRename(null)}
          onRenamed={() => {
            setSequenceToRename(null);
            queryClient.invalidateQueries({ queryKey: ['saas-sequences'] });
          }}
        />
      )}

      {/* Modal Excluir Sequência */}
      {sequenceToDelete && (
        <DeleteSequenceModal
          sequence={sequenceToDelete}
          onClose={() => setSequenceToDelete(null)}
          onDeleted={() => {
            setSequenceToDelete(null);
            queryClient.invalidateQueries({ queryKey: ['saas-sequences'] });
          }}
        />
      )}
    </div>
  );
}

/* ═════════════════════════════════════════════════════════════════════════
   SEQUENCE DETAIL / EDITOR VIEW (Paridade com ChatbotX SequenceEditor)
   ═════════════════════════════════════════════════════════════════════════ */
function SequenceDetailView({
  sequence,
  blueprints,
  onBack,
  onProcessDue,
  isProcessingDue,
}: {
  sequence: SequenceItem;
  blueprints: Array<{ id: number | string; title?: string; name?: string }>;
  onBack: () => void;
  onProcessDue: () => void;
  isProcessingDue: boolean;
}) {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'steps' | 'contacts'>('steps');
  const [isEnrollOpen, setIsEnrollOpen] = useState(false);

  // Adicionar passo
  const addStepMutation = useMutation({
    mutationFn: () =>
      sequencesApi.addStep(sequence.id, {
        order: sequence.steps?.length || 0,
        delay_days: 1,
        delay_minutes: 0,
        delay_unit: 'days',
        is_active: true,
        anytime: true,
        send_time_start: '09:00',
        send_time_end: '18:00',
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['saas-sequence', sequence.id] });
      toast.success('Novo passo adicionado à régua.');
    },
    onError: () => toast.error('Erro ao adicionar passo.'),
  });

  const steps = sequence.steps || [];
  const stats = sequence.stats || { sent: 0, delivered: 0, seen: 0, clicked: 0, failed: 0 };

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6 text-zinc-100">
      {/* Breadcrumb & Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-zinc-800/80 pb-5">
        <div>
          <div className="flex items-center gap-2 text-xs text-zinc-400 mb-1">
            <button
              onClick={onBack}
              className="hover:text-zinc-200 transition flex items-center gap-1"
            >
              <ArrowLeft className="w-3 h-3" />
              Sequências
            </button>
            <ChevronRight className="w-3 h-3 text-zinc-600" />
            <span className="text-zinc-200 font-semibold">{sequence.name}</span>
          </div>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold text-zinc-100">{sequence.name}</h1>
            <span
              className={`px-2 py-0.5 rounded-full text-xs font-medium border ${
                sequence.active
                  ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                  : 'bg-zinc-800 text-zinc-400 border-zinc-700'
              }`}
            >
              {sequence.active ? 'Ativa' : 'Pausada'}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={onProcessDue}
            disabled={isProcessingDue}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-xs text-zinc-200 border border-zinc-700/60 transition"
          >
            <Play className={`w-3.5 h-3.5 text-emerald-400 ${isProcessingDue ? 'animate-spin' : ''}`} />
            Disparar Pendentes
          </button>
          <button
            onClick={() => setIsEnrollOpen(true)}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 text-xs font-semibold text-white transition shadow-lg shadow-purple-900/30"
          >
            <UserPlus className="w-3.5 h-3.5" />
            Inscrever Leads
          </button>
        </div>
      </div>

      {/* Stats Header Bar (Padrão ChatbotX stats bar) */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 p-4 bg-zinc-900/60 border border-zinc-800/80 rounded-xl shadow-lg">
        <div className="flex flex-col items-center justify-center p-2 rounded-lg bg-zinc-950/40">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400 flex items-center gap-1">
            <Send className="w-3 h-3 text-sky-400" /> Enviados
          </span>
          <span className="text-lg font-bold text-zinc-100 mt-0.5">{stats.sent}</span>
        </div>
        <div className="flex flex-col items-center justify-center p-2 rounded-lg bg-zinc-950/40">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400 flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3 text-emerald-400" /> Entregues
          </span>
          <span className="text-lg font-bold text-zinc-100 mt-0.5">{stats.delivered}</span>
        </div>
        <div className="flex flex-col items-center justify-center p-2 rounded-lg bg-zinc-950/40">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400 flex items-center gap-1">
            <Eye className="w-3 h-3 text-purple-400" /> Vistos
          </span>
          <span className="text-lg font-bold text-zinc-100 mt-0.5">{stats.seen}</span>
        </div>
        <div className="flex flex-col items-center justify-center p-2 rounded-lg bg-zinc-950/40">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400 flex items-center gap-1">
            <MousePointer className="w-3 h-3 text-amber-400" /> Clicados
          </span>
          <span className="text-lg font-bold text-zinc-100 mt-0.5">{stats.clicked}</span>
        </div>
        <div className="flex flex-col items-center justify-center p-2 rounded-lg bg-zinc-950/40">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400 flex items-center gap-1">
            <XCircle className="w-3 h-3 text-rose-400" /> Falhas
          </span>
          <span className="text-lg font-bold text-zinc-100 mt-0.5">{stats.failed}</span>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-zinc-800">
        <button
          onClick={() => setActiveTab('steps')}
          className={`pb-3 px-4 text-sm font-semibold border-b-2 transition flex items-center gap-2 ${
            activeTab === 'steps'
              ? 'border-purple-500 text-purple-400'
              : 'border-transparent text-zinc-400 hover:text-zinc-200'
          }`}
        >
          <Layers className="w-4 h-4" />
          Passos da Régua ({steps.length})
        </button>
        <button
          onClick={() => setActiveTab('contacts')}
          className={`pb-3 px-4 text-sm font-semibold border-b-2 transition flex items-center gap-2 ${
            activeTab === 'contacts'
              ? 'border-purple-500 text-purple-400'
              : 'border-transparent text-zinc-400 hover:text-zinc-200'
          }`}
        >
          <Users className="w-4 h-4" />
          Leads Inscritos ({sequence.subscribers})
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === 'steps' ? (
        <div className="space-y-4">
          {steps.length === 0 ? (
            <div className="py-16 text-center border-2 border-dashed border-zinc-800 rounded-xl space-y-3">
              <Layers className="w-10 h-10 mx-auto text-zinc-600" />
              <p className="text-sm font-semibold text-zinc-300">Nenhum passo criado nesta sequência</p>
              <p className="text-xs text-zinc-500 max-w-sm mx-auto">
                Adicione mensagens ou fluxos visuais que serão entregues progressivamente aos contatos.
              </p>
              <button
                onClick={() => addStepMutation.mutate()}
                className="mt-2 inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold transition"
              >
                <Plus className="w-4 h-4" />
                Adicionar Primeiro Passo
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              {steps.map((step, idx) => (
                <SequenceStepCard
                  key={step.id}
                  step={step}
                  stepNumber={idx + 1}
                  sequenceId={sequence.id}
                  blueprints={blueprints}
                />
              ))}

              <button
                onClick={() => addStepMutation.mutate()}
                disabled={addStepMutation.isPending}
                className="w-full py-3.5 border-2 border-dashed border-purple-500/30 hover:border-purple-500/60 rounded-xl flex items-center justify-center gap-2 text-purple-400 hover:text-purple-300 text-xs font-semibold transition hover:bg-purple-500/5"
              >
                <Plus className="w-4 h-4" />
                Adicionar Próximo Passo
              </button>
            </div>
          )}
        </div>
      ) : (
        <SequenceContactsTable sequenceId={sequence.id} />
      )}

      {/* Modal Inscrever Leads */}
      {isEnrollOpen && (
        <EnrollLeadModal
          sequenceId={sequence.id}
          onClose={() => setIsEnrollOpen(false)}
          onEnrolled={() => {
            setIsEnrollOpen(false);
            queryClient.invalidateQueries({ queryKey: ['saas-sequence', sequence.id] });
          }}
        />
      )}
    </div>
  );
}

/* ═════════════════════════════════════════════════════════════════════════
   STEP CARD COMPONENT (Paridade com ChatbotX SequenceStepCard)
   ═════════════════════════════════════════════════════════════════════════ */
function SequenceStepCard({
  step,
  stepNumber,
  sequenceId,
  blueprints,
}: {
  step: SequenceStepItem;
  stepNumber: number;
  sequenceId: number;
  blueprints: Array<{ id: number | string; title?: string; name?: string }>;
}) {
  const queryClient = useQueryClient();
  const [isExpanded, setIsExpanded] = useState(false);
  const [flowId, setFlowId] = useState(step.flow_id || '');
  const [messageTemplate, setMessageTemplate] = useState(step.message_template || '');
  const [delayValue, setDelayValue] = useState(step.delay_days || 1);
  const [delayUnit, setDelayUnit] = useState(step.delay_unit || 'days');
  const [anytime, setAnytime] = useState(step.anytime ?? true);
  const [sendTimeStart, setSendTimeStart] = useState(step.send_time_start || '09:00');
  const [sendTimeEnd, setSendTimeEnd] = useState(step.send_time_end || '18:00');
  const [sendDays, setSendDays] = useState<string[]>(step.send_days || DAYS_OF_WEEK.map((d) => d.id));

  const updateMutation = useMutation({
    mutationFn: (body: Partial<SequenceStepItem>) =>
      sequencesApi.updateStep(sequenceId, step.id, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['saas-sequence', sequenceId] });
      toast.success('Configurações do passo salvas.');
    },
    onError: () => toast.error('Erro ao salvar passo.'),
  });

  const deleteMutation = useMutation({
    mutationFn: () => sequencesApi.deleteStep(sequenceId, step.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['saas-sequence', sequenceId] });
      toast.success('Passo excluído.');
    },
    onError: () => toast.error('Erro ao excluir passo.'),
  });

  const toggleDay = (dayId: string) => {
    const updated = sendDays.includes(dayId)
      ? sendDays.filter((d) => d !== dayId)
      : [...sendDays, dayId];
    setSendDays(updated);
    updateMutation.mutate({ send_days: updated });
  };

  return (
    <div className="bg-zinc-900/90 border border-zinc-800 rounded-xl overflow-hidden shadow-lg">
      {/* Main Row */}
      <div className="p-4 flex flex-wrap items-center justify-between gap-4">
        {/* Esquerda: Número do Passo + Switch + Seletor de Conteúdo */}
        <div className="flex items-center gap-3 flex-1 min-w-[280px]">
          <div className="w-7 h-7 rounded-lg bg-zinc-800 border border-zinc-700/80 text-zinc-300 text-xs font-bold flex items-center justify-center shadow-inner">
            {stepNumber}
          </div>

          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={step.is_active}
              onChange={(e) => updateMutation.mutate({ is_active: e.target.checked })}
              className="sr-only peer"
            />
            <div className="w-9 h-5 bg-zinc-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-zinc-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-purple-600" />
          </label>

          <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
            Enviar:
          </span>

          <select
            value={flowId}
            onChange={(e) => {
              const val = e.target.value;
              setFlowId(val);
              updateMutation.mutate({ flow_id: val || null });
            }}
            className="flex-1 max-w-xs py-1.5 px-3 bg-zinc-950 border border-zinc-800 rounded-lg text-xs text-zinc-200 focus:outline-none focus:border-purple-500 transition"
          >
            <option value="">Texto / Template Simples</option>
            {blueprints.map((bp) => (
              <option key={bp.id} value={bp.id}>
                ⚡ Fluxo: {bp.title || bp.name}
              </option>
            ))}
          </select>
        </div>

        {/* Meio: Delay Selector */}
        <div className="flex items-center gap-2 bg-zinc-950/60 px-3 py-1.5 rounded-lg border border-zinc-800/80">
          <Clock className="w-3.5 h-3.5 text-purple-400" />
          <span className="text-xs text-zinc-400">Após</span>
          <input
            type="number"
            min="1"
            value={delayValue}
            onChange={(e) => {
              const val = parseInt(e.target.value) || 1;
              setDelayValue(val);
              updateMutation.mutate({ delay_days: val });
            }}
            className="w-14 px-2 py-1 bg-zinc-900 border border-zinc-700/80 rounded text-xs text-center text-zinc-200 focus:outline-none focus:border-purple-500"
          />
          <select
            value={delayUnit}
            onChange={(e) => {
              const val = e.target.value;
              setDelayUnit(val);
              updateMutation.mutate({ delay_unit: val });
            }}
            className="py-1 px-2 bg-zinc-900 border border-zinc-700/80 rounded text-xs text-zinc-200 focus:outline-none focus:border-purple-500"
          >
            <option value="hours">Horas</option>
            <option value="days">Dias</option>
            <option value="minutes">Minutos</option>
          </select>
        </div>

        {/* Direita: Métricas Rápidas & Ações */}
        <div className="flex items-center gap-3">
          <div className="hidden sm:flex items-center gap-2 text-[11px] font-medium text-zinc-400 bg-zinc-950/40 px-3 py-1.5 rounded-lg border border-zinc-800/50">
            <span title="Enviados" className="flex items-center gap-1 text-sky-400">
              <Send className="w-3 h-3" /> {step.sent_count || 0}
            </span>
            <span>•</span>
            <span title="Entregues" className="flex items-center gap-1 text-emerald-400">
              <CheckCircle2 className="w-3 h-3" /> {step.delivered_count || 0}
            </span>
            <span>•</span>
            <span title="Falhas" className="flex items-center gap-1 text-rose-400">
              <XCircle className="w-3 h-3" /> {step.failed_count || 0}
            </span>
          </div>

          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-1.5 hover:bg-zinc-800 rounded-lg text-zinc-400 hover:text-zinc-200 transition"
            title="Horários e dias permitidos"
          >
            <ChevronDown className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
          </button>

          <button
            onClick={() => deleteMutation.mutate()}
            className="p-1.5 hover:bg-rose-500/20 rounded-lg text-zinc-400 hover:text-rose-400 transition"
            title="Remover passo"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Se não escolheu Fluxo, exibe editor de texto rápido */}
      {!flowId && (
        <div className="px-4 pb-3">
          <textarea
            placeholder="Digite a mensagem de texto deste passo... Use {{nome}} para personalizar."
            value={messageTemplate}
            onChange={(e) => setMessageTemplate(e.target.value)}
            onBlur={() => updateMutation.mutate({ message_template: messageTemplate })}
            rows={2}
            className="w-full p-2.5 bg-zinc-950/70 border border-zinc-800 rounded-lg text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-purple-500 transition"
          />
        </div>
      )}

      {/* Janela de Horário e Dias da Semana (Expandable Drawer) */}
      {isExpanded && (
        <div className="p-4 bg-zinc-950/80 border-t border-zinc-800/80 space-y-4 text-xs">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <span className="font-semibold text-zinc-300">Horário de Envio:</span>
              <label className="inline-flex items-center gap-1.5 text-zinc-400 cursor-pointer">
                <input
                  type="radio"
                  name={`time-opt-${step.id}`}
                  checked={anytime}
                  onChange={() => {
                    setAnytime(true);
                    updateMutation.mutate({ anytime: true });
                  }}
                  className="accent-purple-600"
                />
                Qualquer horário
              </label>
              <label className="inline-flex items-center gap-1.5 text-zinc-400 cursor-pointer">
                <input
                  type="radio"
                  name={`time-opt-${step.id}`}
                  checked={!anytime}
                  onChange={() => {
                    setAnytime(false);
                    updateMutation.mutate({ anytime: false });
                  }}
                  className="accent-purple-600"
                />
                Entre horários específicos
              </label>
            </div>

            {!anytime && (
              <div className="flex items-center gap-2">
                <input
                  type="time"
                  value={sendTimeStart}
                  onChange={(e) => {
                    setSendTimeStart(e.target.value);
                    updateMutation.mutate({ send_time_start: e.target.value });
                  }}
                  className="bg-zinc-900 border border-zinc-700 px-2 py-1 rounded text-zinc-200"
                />
                <span className="text-zinc-500">às</span>
                <input
                  type="time"
                  value={sendTimeEnd}
                  onChange={(e) => {
                    setSendTimeEnd(e.target.value);
                    updateMutation.mutate({ send_time_end: e.target.value });
                  }}
                  className="bg-zinc-900 border border-zinc-700 px-2 py-1 rounded text-zinc-200"
                />
              </div>
            )}
          </div>

          <div className="flex items-center gap-2">
            <span className="font-semibold text-zinc-300 mr-2">Dias Permitidos:</span>
            {DAYS_OF_WEEK.map((day) => {
              const active = sendDays.includes(day.id);
              return (
                <button
                  key={day.id}
                  onClick={() => toggleDay(day.id)}
                  type="button"
                  className={`px-2.5 py-1 rounded text-[11px] font-semibold transition border ${
                    active
                      ? 'bg-purple-600/20 text-purple-300 border-purple-500/40'
                      : 'bg-zinc-900 text-zinc-500 border-zinc-800 hover:text-zinc-300'
                  }`}
                >
                  {day.label}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

/* ═════════════════════════════════════════════════════════════════════════
   ENROLLED CONTACTS TABLE (Paridade com ChatbotX Sequence Contacts)
   ═════════════════════════════════════════════════════════════════════════ */
function SequenceContactsTable({ sequenceId }: { sequenceId: number }) {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ['saas-sequence-contacts', sequenceId],
    queryFn: () => sequencesApi.contacts(sequenceId),
  });

  const contacts: EnrolledContactItem[] = data?.contacts || [];

  const unenrollMutation = useMutation({
    mutationFn: (leadId: number) => sequencesApi.unenroll(sequenceId, leadId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['saas-sequence-contacts', sequenceId] });
      queryClient.invalidateQueries({ queryKey: ['saas-sequence', sequenceId] });
      toast.success('Inscrição cancelada com sucesso.');
    },
  });

  if (isLoading) {
    return <div className="py-12 text-center text-zinc-500 text-xs">Carregando inscritos...</div>;
  }

  if (contacts.length === 0) {
    return (
      <div className="py-12 text-center border border-zinc-800/80 rounded-xl space-y-2">
        <Users className="w-8 h-8 mx-auto text-zinc-600" />
        <p className="text-xs text-zinc-400 font-medium">Nenhum contato inscrito nesta sequência no momento.</p>
      </div>
    );
  }

  return (
    <div className="bg-zinc-900/50 border border-zinc-800 rounded-xl overflow-hidden shadow-lg">
      <table className="w-full text-left border-collapse text-xs">
        <thead>
          <tr className="border-b border-zinc-800/80 bg-zinc-950/40 text-[11px] font-semibold text-zinc-400 uppercase tracking-wider">
            <th className="py-3 px-4">Nome / Contato</th>
            <th className="py-3 px-4">Telefone</th>
            <th className="py-3 px-4 text-center">Passo Atual</th>
            <th className="py-3 px-4 text-center">Status</th>
            <th className="py-3 px-4">Próximo Disparo</th>
            <th className="py-3 px-4">Inscrito em</th>
            <th className="py-3 px-4 text-right">Ação</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-800/40">
          {contacts.map((c: EnrolledContactItem) => (
            <tr key={c.id} className="hover:bg-zinc-800/20 transition">
              <td className="py-3 px-4 font-semibold text-zinc-200">{c.name}</td>
              <td className="py-3 px-4 text-zinc-400">{c.phone}</td>
              <td className="py-3 px-4 text-center font-bold text-purple-400">
                Passo {c.current_step + 1}
              </td>
              <td className="py-3 px-4 text-center">
                <span
                  className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border ${
                    c.status === 'active'
                      ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                      : c.status === 'completed'
                      ? 'bg-purple-500/10 text-purple-300 border-purple-500/30'
                      : 'bg-zinc-800 text-zinc-400 border-zinc-700'
                  }`}
                >
                  {c.status}
                </span>
              </td>
              <td className="py-3 px-4 text-zinc-300">
                {c.next_run_at ? new Date(c.next_run_at).toLocaleString('pt-BR') : '—'}
              </td>
              <td className="py-3 px-4 text-zinc-400">
                {c.enrolled_at ? new Date(c.enrolled_at).toLocaleDateString('pt-BR') : '—'}
              </td>
              <td className="py-3 px-4 text-right">
                {c.status === 'active' && (
                  <button
                    onClick={() => unenrollMutation.mutate(c.lead_id)}
                    className="p-1 text-zinc-500 hover:text-rose-400 transition"
                    title="Cancelar inscrição"
                  >
                    <UserMinus className="w-3.5 h-3.5" />
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ═════════════════════════════════════════════════════════════════════════
   MODAIS AUXILIARES (Zero Dialogs Nativos)
   ═════════════════════════════════════════════════════════════════════════ */
function CreateSequenceModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: (seq: SequenceItem) => void;
}) {
  const [name, setName] = useState('');
  const [folderName, setFolderName] = useState('');

  const createMutation = useMutation({
    mutationFn: () => sequencesApi.create({ name, folder_name: folderName }),
    onSuccess: (res) => {
      toast.success('Sequência criada com sucesso!');
      onCreated(res.sequence);
    },
    onError: () => toast.error('Erro ao criar sequência.'),
  });

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-zinc-900 border border-zinc-800 rounded-xl p-6 shadow-2xl space-y-4">
        <h3 className="text-base font-bold text-zinc-100 flex items-center gap-2">
          <GitBranch className="w-4 h-4 text-purple-400" />
          Nova Sequência de Nutrição
        </h3>
        <p className="text-xs text-zinc-400">
          Dê um nome para a sua esteira automática de mensagens e fluxos.
        </p>

        <div className="space-y-3">
          <div>
            <label className="block text-xs font-semibold text-zinc-300 mb-1">
              Nome da Sequência *
            </label>
            <input
              type="text"
              placeholder="Ex: Onboarding 7 Dias VIP"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded-lg text-sm text-zinc-100 focus:outline-none focus:border-purple-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-zinc-300 mb-1">
              Pasta (opcional)
            </label>
            <input
              type="text"
              placeholder="Ex: Lançamentos 2026"
              value={folderName}
              onChange={(e) => setFolderName(e.target.value)}
              className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded-lg text-sm text-zinc-100 focus:outline-none focus:border-purple-500"
            />
          </div>
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="px-3.5 py-1.5 text-xs font-medium text-zinc-400 hover:text-zinc-200 transition"
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={() => createMutation.mutate()}
            disabled={!name.trim() || createMutation.isPending}
            className="px-4 py-2 text-xs font-semibold rounded-lg bg-purple-600 hover:bg-purple-500 text-white transition disabled:opacity-50"
          >
            {createMutation.isPending ? 'Criando...' : 'Criar Sequência'}
          </button>
        </div>
      </div>
    </div>
  );
}

function RenameSequenceModal({
  sequence,
  onClose,
  onRenamed,
}: {
  sequence: SequenceItem;
  onClose: () => void;
  onRenamed: () => void;
}) {
  const [name, setName] = useState(sequence.name);
  const renameMutation = useMutation({
    mutationFn: () => sequencesApi.rename(sequence.id, name),
    onSuccess: () => {
      toast.success('Sequência renomeada.');
      onRenamed();
    },
    onError: () => toast.error('Erro ao renomear.'),
  });

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="w-full max-w-sm bg-zinc-900 border border-zinc-800 rounded-xl p-6 shadow-2xl space-y-4">
        <h3 className="text-base font-bold text-zinc-100">Renomear Sequência</h3>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded-lg text-sm text-zinc-100 focus:outline-none focus:border-purple-500"
        />
        <div className="flex justify-end gap-2 pt-2">
          <button
            onClick={onClose}
            className="px-3.5 py-1.5 text-xs font-medium text-zinc-400 hover:text-zinc-200 transition"
          >
            Cancelar
          </button>
          <button
            onClick={() => renameMutation.mutate()}
            disabled={!name.trim() || renameMutation.isPending}
            className="px-4 py-2 text-xs font-semibold rounded-lg bg-purple-600 hover:bg-purple-500 text-white transition"
          >
            Salvar
          </button>
        </div>
      </div>
    </div>
  );
}

function DeleteSequenceModal({
  sequence,
  onClose,
  onDeleted,
}: {
  sequence: SequenceItem;
  onClose: () => void;
  onDeleted: () => void;
}) {
  const deleteMutation = useMutation({
    mutationFn: () => sequencesApi.delete(sequence.id),
    onSuccess: () => {
      toast.success('Sequência excluída.');
      onDeleted();
    },
    onError: () => toast.error('Erro ao excluir sequência.'),
  });

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="w-full max-w-sm bg-zinc-900 border border-rose-900/50 rounded-xl p-6 shadow-2xl space-y-4">
        <h3 className="text-base font-bold text-rose-400 flex items-center gap-2">
          <AlertCircle className="w-5 h-5 text-rose-500" />
          Excluir Sequência?
        </h3>
        <p className="text-xs text-zinc-400">
          Tem certeza que deseja excluir <strong>"{sequence.name}"</strong>? Todos os passos e o progresso dos inscritos serão removidos.
        </p>
        <div className="flex justify-end gap-2 pt-2">
          <button
            onClick={onClose}
            className="px-3.5 py-1.5 text-xs font-medium text-zinc-400 hover:text-zinc-200 transition"
          >
            Cancelar
          </button>
          <button
            onClick={() => deleteMutation.mutate()}
            disabled={deleteMutation.isPending}
            className="px-4 py-2 text-xs font-semibold rounded-lg bg-rose-600 hover:bg-rose-500 text-white transition"
          >
            {deleteMutation.isPending ? 'Excluindo...' : 'Sim, Excluir'}
          </button>
        </div>
      </div>
    </div>
  );
}

function EnrollLeadModal({
  sequenceId,
  onClose,
  onEnrolled,
}: {
  sequenceId: number;
  onClose: () => void;
  onEnrolled: () => void;
}) {
  const [selectedLeads, setSelectedLeads] = useState<number[]>([]);
  const { data: leadsData, isLoading } = useQuery({
    queryKey: ['inbox-leads-enroll'],
    queryFn: () => inboxApi.getLeads({ limit: 100 }),
  });

  const leads = leadsData?.items || [];

  const enrollMutation = useMutation({
    mutationFn: () => sequencesApi.enroll(sequenceId, selectedLeads),
    onSuccess: (res) => {
      toast.success(res.message);
      onEnrolled();
    },
    onError: () => toast.error('Erro ao inscrever contatos.'),
  });

  const toggleLead = (id: number) => {
    setSelectedLeads((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="w-full max-w-lg bg-zinc-900 border border-zinc-800 rounded-xl p-6 shadow-2xl space-y-4">
        <h3 className="text-base font-bold text-zinc-100 flex items-center gap-2">
          <UserPlus className="w-4 h-4 text-purple-400" />
          Inscrever Leads na Sequência
        </h3>
        <p className="text-xs text-zinc-400">
          Selecione quais contatos devem entrar imediatamente na régua de nutrição:
        </p>

        <div className="max-h-64 overflow-y-auto border border-zinc-800 rounded-lg divide-y divide-zinc-800/60">
          {isLoading ? (
            <div className="py-8 text-center text-xs text-zinc-500">Carregando contatos...</div>
          ) : leads.length === 0 ? (
            <div className="py-8 text-center text-xs text-zinc-500">Nenhum lead encontrado</div>
          ) : (
            leads.map((l: { id: number; nome?: string | null; telefone: string }) => {
              const checked = selectedLeads.includes(l.id);
              return (
                <div
                  key={l.id}
                  onClick={() => toggleLead(l.id)}
                  className="p-3 flex items-center justify-between hover:bg-zinc-800/40 cursor-pointer text-xs transition"
                >
                  <div>
                    <p className="font-semibold text-zinc-200">{l.nome || 'Sem nome'}</p>
                    <p className="text-[11px] text-zinc-500">{l.telefone}</p>
                  </div>
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => {}}
                    className="accent-purple-600 rounded"
                  />
                </div>
              );
            })
          )}
        </div>

        <div className="flex items-center justify-between pt-2">
          <span className="text-xs text-zinc-400">
            {selectedLeads.length} contato(s) selecionado(s)
          </span>
          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="px-3.5 py-1.5 text-xs font-medium text-zinc-400 hover:text-zinc-200 transition"
            >
              Cancelar
            </button>
            <button
              onClick={() => enrollMutation.mutate()}
              disabled={selectedLeads.length === 0 || enrollMutation.isPending}
              className="px-4 py-2 text-xs font-semibold rounded-lg bg-purple-600 hover:bg-purple-500 text-white transition disabled:opacity-50"
            >
              {enrollMutation.isPending ? 'Inscrevendo...' : 'Inscrever Selecionados'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
