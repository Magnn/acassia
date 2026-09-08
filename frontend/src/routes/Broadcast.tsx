import { useState, useEffect, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Megaphone,
  Plus,
  Users,
  CheckCircle2,
  XCircle,
  Clock,
  CalendarClock,
  Send,
  ShieldCheck,
  Smartphone,
  ChevronRight,
  ChevronLeft,
  Search,
  X,
  Eye,
  Trash2,
  AlertTriangle,
  RefreshCw,
  Image as ImageIcon,
  Check,
  FileText,
  Sparkles,
} from 'lucide-react';
import { broadcastApi, type Campaign } from '../api/saas';
import { handleApiError } from '../lib/handleApiError';
import { toast } from '../lib/toast';

export default function Broadcast() {
  const qc = useQueryClient();
  const [showWizard, setShowWizard] = useState(false);
  const [selectedStatusTab, setSelectedStatusTab] = useState<string>('all');
  const [inspectCampaignId, setInspectCampaignId] = useState<number | null>(null);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['broadcast-campaigns'],
    queryFn: broadcastApi.campaigns,
    refetchInterval: 10000, // Atualiza a cada 10s caso haja envios ativos
  });

  const campaigns = data?.campaigns ?? [];

  // KPIs
  const totalCampaigns = campaigns.length;
  const totalRecipients = campaigns.reduce((acc, c) => acc + (c.total_recipients || 0), 0);
  const totalDelivered = campaigns.reduce((acc, c) => acc + (c.delivered_count || c.total_delivered || c.sent_count || 0), 0);
  const deliveryRate = totalRecipients > 0 ? Math.round((totalDelivered / totalRecipients) * 100) : 100;

  // Filtro por abas
  const filteredCampaigns = useMemo(() => {
    if (selectedStatusTab === 'all') return campaigns;
    if (selectedStatusTab === 'draft') return campaigns.filter(c => c.status === 'draft');
    if (selectedStatusTab === 'scheduled') return campaigns.filter(c => c.status === 'scheduled');
    if (selectedStatusTab === 'sending') return campaigns.filter(c => c.status === 'sending');
    if (selectedStatusTab === 'completed') return campaigns.filter(c => c.status === 'completed' || c.status === 'sent');
    return campaigns;
  }, [campaigns, selectedStatusTab]);

  return (
    <div className="p-6 md:p-10 max-w-6xl mx-auto space-y-8 animate-in fade-in duration-300">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="w-11 h-11 rounded-2xl bg-accent-amethyst/15 border border-accent-amethyst/30 flex items-center justify-center shadow-lg shadow-accent-amethyst/10">
              <Megaphone className="w-5 h-5 text-accent-amethyst" />
            </div>
            <div>
              <h1 className="text-2xl md:text-3xl font-black tracking-tight">Disparos em Massa (Broadcast)</h1>
              <p className="text-secondary text-xs md:text-sm font-medium">
                Engaje sua base no WhatsApp com segmentação precisa, proteção anti-ban e templates de alta conversão.
              </p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => refetch()}
            className="p-3 bg-bg-surface hover:bg-bg-surface/80 border border-border rounded-2xl text-secondary hover:text-white transition-all"
            title="Atualizar lista"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={() => setShowWizard(true)}
            className="flex items-center gap-2 px-5 py-3 bg-accent-amethyst hover:bg-accent-amethyst/90 text-white rounded-2xl font-black uppercase tracking-widest text-xs transition-all shadow-lg shadow-accent-amethyst/20"
          >
            <Plus className="w-4 h-4" /> Nova Campanha
          </button>
        </div>
      </div>

      {/* KPI Stats Bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-bg-surface border border-border rounded-2xl p-5 relative overflow-hidden">
          <div className="text-[10px] font-black uppercase tracking-widest text-secondary mb-1">Campanhas Totais</div>
          <div className="text-2xl font-black">{totalCampaigns}</div>
          <div className="text-[11px] text-secondary mt-1">Histórico completo</div>
        </div>
        <div className="bg-bg-surface border border-border rounded-2xl p-5 relative overflow-hidden">
          <div className="text-[10px] font-black uppercase tracking-widest text-secondary mb-1">Impacto Total</div>
          <div className="text-2xl font-black text-accent-amethyst">{totalRecipients.toLocaleString('pt-BR')}</div>
          <div className="text-[11px] text-secondary mt-1">Leads segmentados</div>
        </div>
        <div className="bg-bg-surface border border-border rounded-2xl p-5 relative overflow-hidden">
          <div className="text-[10px] font-black uppercase tracking-widest text-secondary mb-1">Entregas no WhatsApp</div>
          <div className="text-2xl font-black text-emerald-400">{totalDelivered.toLocaleString('pt-BR')}</div>
          <div className="text-[11px] text-emerald-400/80 font-bold mt-1">{deliveryRate}% de sucesso</div>
        </div>
        <div className="bg-bg-surface border border-border rounded-2xl p-5 relative overflow-hidden">
          <div className="text-[10px] font-black uppercase tracking-widest text-secondary mb-1">Proteção Anti-Ban</div>
          <div className="text-2xl font-black text-indigo-400 flex items-center gap-1.5">
            <ShieldCheck className="w-5 h-5 text-indigo-400" /> Ativa
          </div>
          <div className="text-[11px] text-secondary mt-1">Meta Throttling Shield</div>
        </div>
      </div>

      {/* Status Filter Tabs */}
      <div className="flex items-center gap-2 border-b border-border pb-3 overflow-x-auto">
        {[
          { id: 'all', label: 'Todas', count: campaigns.length },
          { id: 'draft', label: 'Rascunhos', count: campaigns.filter(c => c.status === 'draft').length },
          { id: 'scheduled', label: 'Agendadas', count: campaigns.filter(c => c.status === 'scheduled').length },
          { id: 'sending', label: 'Em Envio', count: campaigns.filter(c => c.status === 'sending').length },
          { id: 'completed', label: 'Concluídas', count: campaigns.filter(c => c.status === 'completed' || c.status === 'sent').length },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setSelectedStatusTab(tab.id)}
            className={`px-4 py-2 rounded-xl text-xs font-black uppercase tracking-wider transition-all flex items-center gap-2 whitespace-nowrap ${
              selectedStatusTab === tab.id
                ? 'bg-accent-amethyst text-white shadow-sm'
                : 'text-secondary hover:text-white hover:bg-bg-surface'
            }`}
          >
            {tab.label}
            <span className={`text-[10px] px-2 py-0.5 rounded-full ${
              selectedStatusTab === tab.id ? 'bg-white/20 text-white' : 'bg-bg-surface border border-border text-secondary'
            }`}>
              {tab.count}
            </span>
          </button>
        ))}
      </div>

      {/* Campaigns List */}
      {isLoading ? (
        <div className="space-y-4 animate-pulse">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-32 bg-bg-surface border border-border rounded-2xl" />
          ))}
        </div>
      ) : filteredCampaigns.length === 0 ? (
        <div className="bg-bg-surface border border-dashed border-border rounded-3xl p-16 text-center max-w-lg mx-auto">
          <div className="w-16 h-16 rounded-3xl bg-accent-amethyst/10 flex items-center justify-center mx-auto mb-4 text-accent-amethyst">
            <Megaphone className="w-8 h-8" />
          </div>
          <h3 className="font-black text-lg mb-2">Nenhuma campanha encontrada</h3>
          <p className="text-secondary text-sm mb-6">
            {selectedStatusTab === 'all'
              ? 'Você ainda não possui disparos criados. Crie sua primeira campanha com segmentação e agendamento inteligente.'
              : 'Nenhuma campanha corresponde ao filtro selecionado.'}
          </p>
          <button
            onClick={() => setShowWizard(true)}
            className="px-6 py-3 bg-accent-amethyst hover:bg-accent-amethyst/90 text-white rounded-2xl text-xs font-black uppercase tracking-widest transition-all shadow-lg shadow-accent-amethyst/20"
          >
            Criar Nova Campanha
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {filteredCampaigns.map(c => (
            <CampaignItemCard
              key={c.id}
              campaign={c}
              onInspect={() => setInspectCampaignId(c.id)}
              onRefresh={() => qc.invalidateQueries({ queryKey: ['broadcast-campaigns'] })}
            />
          ))}
        </div>
      )}

      {/* Wizard Modal */}
      {showWizard && (
        <CreateCampaignWizardModal
          onClose={() => setShowWizard(false)}
          onCreated={() => {
            setShowWizard(false);
            qc.invalidateQueries({ queryKey: ['broadcast-campaigns'] });
          }}
        />
      )}

      {/* Recipients Audit Drawer/Modal */}
      {inspectCampaignId !== null && (
        <RecipientsDrawer
          campaignId={inspectCampaignId}
          onClose={() => setInspectCampaignId(null)}
        />
      )}
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   CAMPAIGN ITEM CARD
   ───────────────────────────────────────────────────────────────────────────── */
function CampaignItemCard({
  campaign: c,
  onInspect,
  onRefresh,
}: {
  campaign: Campaign;
  onInspect: () => void;
  onRefresh: () => void;
}) {
  const sendMut = useMutation({
    mutationFn: () => broadcastApi.send(c.id),
    onSuccess: res => {
      toast.success(res.message || `Disparo iniciado para ${res.total_recipients} contatos!`);
      onRefresh();
    },
    onError: handleApiError('Erro ao iniciar disparo'),
  });

  const deleteMut = useMutation({
    mutationFn: () => broadcastApi.delete(c.id),
    onSuccess: () => {
      toast.success('Campanha removida.');
      onRefresh();
    },
    onError: handleApiError('Erro ao remover campanha'),
  });

  const title = c.title || c.name || 'Campanha Sem Nome';
  const message = c.message_text || c.message_template || '';
  const delivered = c.delivered_count || c.total_delivered || c.sent_count || 0;
  const total = c.total_recipients || 0;
  const progressPercent = total > 0 ? Math.min(100, Math.round((delivered / total) * 100)) : 0;

  const statusConfig: Record<string, { color: string; label: string; Icon: typeof Clock }> = {
    draft: { color: 'text-amber-400 bg-amber-500/10 border-amber-500/30', label: 'Rascunho', Icon: Clock },
    scheduled: { color: 'text-blue-400 bg-blue-500/10 border-blue-500/30', label: 'Agendado', Icon: CalendarClock },
    sending: { color: 'text-purple-400 bg-purple-500/10 border-purple-500/30 animate-pulse', label: 'Enviando...', Icon: Send },
    sent: { color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30', label: 'Concluído', Icon: CheckCircle2 },
    completed: { color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30', label: 'Concluído', Icon: CheckCircle2 },
    cancelled: { color: 'text-zinc-400 bg-zinc-500/10 border-zinc-500/30', label: 'Cancelado', Icon: XCircle },
    failed: { color: 'text-red-400 bg-red-500/10 border-red-500/30', label: 'Falhou', Icon: XCircle },
  };
  const cfg = statusConfig[c.status] || statusConfig.draft;
  const StatusIcon = cfg.Icon;

  // Segment tag badges
  const filterTags = (c.segment_filters?.tags as string[]) || [];
  const antiBanDelay = (c.segment_filters?.anti_ban_delay_seconds as number) || 2;

  return (
    <div className="bg-bg-surface border border-border hover:border-accent-amethyst/30 rounded-2xl p-5 md:p-6 transition-all shadow-sm">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
        <div className="space-y-1 max-w-2xl">
          <div className="flex items-center gap-3">
            <h3 className="font-black text-base text-white">{title}</h3>
            <span className={`text-[10px] font-black uppercase tracking-widest px-2.5 py-1 rounded-lg border flex items-center gap-1.5 ${cfg.color}`}>
              <StatusIcon className="w-3 h-3" />
              {cfg.label}
            </span>
            {c.message_media_url && (
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-white/5 border border-border text-secondary flex items-center gap-1">
                <ImageIcon className="w-3 h-3 text-accent-amethyst" /> Mídia
              </span>
            )}
          </div>
          <p className="text-xs text-secondary line-clamp-2 font-mono bg-bg-primary/40 px-3 py-1.5 rounded-xl border border-border/40 mt-1">
            {message}
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2 self-start md:self-center shrink-0">
          <button
            onClick={onInspect}
            className="flex items-center gap-1.5 px-3.5 py-2 bg-bg-primary hover:bg-bg-primary/80 border border-border rounded-xl text-xs font-bold text-secondary hover:text-white transition-all"
            title="Ver destinatários e logs"
          >
            <Eye className="w-3.5 h-3.5 text-accent-amethyst" /> Destinatários & Logs
          </button>

          {(c.status === 'draft' || c.status === 'scheduled') && (
            <button
              onClick={() => sendMut.mutate()}
              disabled={sendMut.isPending}
              className="flex items-center gap-1.5 px-4 py-2 bg-accent-amethyst/15 hover:bg-accent-amethyst/25 border border-accent-amethyst/30 text-accent-amethyst rounded-xl text-xs font-black uppercase tracking-wider transition-all"
            >
              <Send className="w-3.5 h-3.5" />
              {sendMut.isPending ? 'Iniciando...' : 'Disparar Agora'}
            </button>
          )}

          {c.status === 'sending' && (
            <button
              onClick={() => deleteMut.mutate()}
              disabled={deleteMut.isPending}
              className="flex items-center gap-1.5 px-3 py-2 bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 text-red-400 rounded-xl text-xs font-bold transition-all"
            >
              <XCircle className="w-3.5 h-3.5" /> Cancelar
            </button>
          )}

          {c.status !== 'sending' && (
            <button
              onClick={() => {
                if (window.confirm('Excluir esta campanha?')) {
                  deleteMut.mutate();
                }
              }}
              className="p-2 hover:bg-red-500/10 text-secondary hover:text-red-400 rounded-xl transition-all"
              title="Excluir campanha"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Details & Metrics bar */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-3 border-t border-border/50 text-xs text-secondary">
        <div className="flex items-center gap-2">
          <Users className="w-3.5 h-3.5 text-accent-amethyst" />
          <span><strong className="text-white font-bold">{total}</strong> destinatários</span>
        </div>
        <div className="flex items-center gap-2">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
          <span><strong className="text-white font-bold">{delivered}</strong> entregues</span>
        </div>
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-3.5 h-3.5 text-indigo-400" />
          <span>Delay anti-ban: <strong className="text-white font-bold">{antiBanDelay}s</strong></span>
        </div>
        <div className="flex items-center gap-2">
          <Clock className="w-3.5 h-3.5 text-secondary" />
          <span>
            {c.scheduled_at
              ? `Agendado: ${new Date(c.scheduled_at).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })}`
              : `Criado: ${new Date(c.created_at).toLocaleDateString('pt-BR')}`}
          </span>
        </div>
      </div>

      {/* Progress Bar if active or done */}
      {(c.status === 'sending' || c.status === 'completed' || c.status === 'sent') && total > 0 && (
        <div className="mt-3 space-y-1.5">
          <div className="flex justify-between text-[10px] font-bold text-secondary">
            <span>Progresso da entrega</span>
            <span>{progressPercent}% ({delivered}/{total})</span>
          </div>
          <div className="w-full bg-bg-primary rounded-full h-2 overflow-hidden border border-border/30">
            <div
              className={`h-full transition-all duration-500 rounded-full ${
                c.status === 'sending' ? 'bg-gradient-to-r from-accent-amethyst to-purple-400' : 'bg-emerald-500'
              }`}
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>
      )}

      {/* Tags chips if present */}
      {filterTags.length > 0 && (
        <div className="flex items-center gap-1.5 mt-3 flex-wrap">
          <span className="text-[10px] uppercase tracking-wider text-secondary font-bold">Filtros:</span>
          {filterTags.map(t => (
            <span key={t} className="text-[10px] px-2 py-0.5 rounded-md bg-accent-amethyst/10 border border-accent-amethyst/20 text-accent-amethyst font-semibold">
              #{t}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   RECIPIENTS AUDIT DRAWER / MODAL
   ───────────────────────────────────────────────────────────────────────────── */
function RecipientsDrawer({ campaignId, onClose }: { campaignId: number; onClose: () => void }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState<string>('all');

  const { data, isLoading } = useQuery({
    queryKey: ['broadcast-recipients', campaignId],
    queryFn: () => broadcastApi.recipients(campaignId),
  });

  const recipients = data?.recipients ?? [];

  const filtered = useMemo(() => {
    return recipients.filter(r => {
      const matchSearch =
        (r.lead_name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
        (r.lead_phone || '').includes(searchTerm);
      const matchStatus = filterStatus === 'all' ? true : r.status === filterStatus;
      return matchSearch && matchStatus;
    });
  }, [recipients, searchTerm, filterStatus]);

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 md:p-6 animate-in fade-in duration-200">
      <div className="bg-bg-surface border border-border rounded-3xl max-w-3xl w-full flex flex-col max-h-[85vh] shadow-2xl overflow-hidden">
        {/* Modal Header */}
        <div className="p-6 border-b border-border flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-accent-amethyst/10 flex items-center justify-center">
              <Users className="w-5 h-5 text-accent-amethyst" />
            </div>
            <div>
              <h2 className="text-lg font-black tracking-tight">Destinatários & Auditoria de Entrega</h2>
              <p className="text-xs text-secondary">
                Auditoria lead a lead da campanha #{campaignId} ({recipients.length} total)
              </p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-bg-primary rounded-xl text-secondary hover:text-white transition-all">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Filters */}
        <div className="p-4 border-b border-border bg-bg-primary/20 flex flex-col sm:flex-row items-center gap-3">
          <div className="relative flex-1 w-full">
            <Search className="w-4 h-4 text-secondary absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Buscar por nome ou telefone..."
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-4 py-2 bg-bg-primary border border-border rounded-xl text-xs focus:border-accent-amethyst outline-none"
            />
          </div>
          <div className="flex items-center gap-1.5 self-end sm:self-center">
            {['all', 'sent', 'pending', 'failed'].map(st => (
              <button
                key={st}
                onClick={() => setFilterStatus(st)}
                className={`px-3 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-wider transition-all ${
                  filterStatus === st ? 'bg-accent-amethyst text-white' : 'bg-bg-primary border border-border text-secondary'
                }`}
              >
                {st === 'all' ? 'Todos' : st === 'sent' ? 'Entregues' : st === 'pending' ? 'Pendentes' : 'Falhas'}
              </button>
            ))}
          </div>
        </div>

        {/* Recipients List */}
        <div className="p-6 overflow-y-auto flex-1 space-y-2">
          {isLoading ? (
            <div className="py-12 text-center text-secondary text-xs animate-pulse">Carregando lista de destinatários...</div>
          ) : filtered.length === 0 ? (
            <div className="py-12 text-center text-secondary text-xs">Nenhum destinatário encontrado com esses filtros.</div>
          ) : (
            filtered.map(r => (
              <div
                key={r.id}
                className="flex items-center justify-between p-3 rounded-xl bg-bg-primary/40 border border-border/50 hover:border-border transition-all"
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-accent-amethyst/10 flex items-center justify-center font-bold text-xs text-accent-amethyst">
                    {(r.lead_name || 'L')[0].toUpperCase()}
                  </div>
                  <div>
                    <div className="font-bold text-xs text-white">{r.lead_name || 'Lead sem nome'}</div>
                    <div className="text-[11px] text-secondary font-mono">{r.lead_phone || 'Sem telefone'}</div>
                  </div>
                </div>

                <div className="flex items-center gap-3 text-right">
                  {r.sent_at && (
                    <span className="text-[10px] text-secondary hidden sm:inline">
                      {new Date(r.sent_at).toLocaleTimeString('pt-BR')}
                    </span>
                  )}
                  {r.status === 'sent' || r.status === 'delivered' ? (
                    <span className="text-[10px] font-bold px-2.5 py-1 rounded-md bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 flex items-center gap-1">
                      <CheckCircle2 className="w-3 h-3" /> Entregue
                    </span>
                  ) : r.status === 'pending' ? (
                    <span className="text-[10px] font-bold px-2.5 py-1 rounded-md bg-amber-500/10 border border-amber-500/30 text-amber-400 flex items-center gap-1">
                      <Clock className="w-3 h-3" /> Na fila
                    </span>
                  ) : (
                    <span className="text-[10px] font-bold px-2.5 py-1 rounded-md bg-red-500/10 border border-red-500/30 text-red-400 flex items-center gap-1" title={r.error_reason || 'Erro desconhecido'}>
                      <XCircle className="w-3 h-3" /> Falhou {r.error_reason ? `(${r.error_reason})` : ''}
                    </span>
                  )}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-border flex justify-end">
          <button onClick={onClose} className="px-5 py-2.5 bg-bg-primary hover:bg-bg-primary/80 border border-border rounded-xl text-xs font-bold text-white">
            Fechar
          </button>
        </div>
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   CREATE CAMPAIGN 4-STEP WIZARD (CHATBOTX PATTERN)
   ───────────────────────────────────────────────────────────────────────────── */
function CreateCampaignWizardModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: () => void;
}) {
  // Wizard Step: 1 = Audiência, 2 = Mensagem & Preview, 3 = Agendamento & Anti-Ban, 4 = Revisão
  const [step, setStep] = useState<1 | 2 | 3 | 4>(1);

  // Form State
  const [name, setName] = useState('');
  const [message, setMessage] = useState('');
  const [mediaUrl, setMediaUrl] = useState('');
  const [mediaType, setMediaType] = useState<'image' | 'video' | 'document'>('image');

  // Segmentation Filters
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [customTagInput, setCustomTagInput] = useState('');
  const [scoreBand, setScoreBand] = useState<string>('all'); // all, hot, warm, cold
  const [excludeOptedOut, setExcludeOptedOut] = useState(true);

  // Scheduling & Anti-Ban
  const [sendMode, setSendMode] = useState<'immediate' | 'scheduled'>('immediate');
  const [scheduledAt, setScheduledAt] = useState('');
  const [antiBanDelaySeconds, setAntiBanDelaySeconds] = useState<number>(5); // 5s recomendado Meta

  // Live audience estimation state
  const [audienceCount, setAudienceCount] = useState<number | null>(null);
  const [audienceSample, setAudienceSample] = useState<Array<{ id: number; nome: string | null; telefone: string }>>([]);
  const [isEstimating, setIsEstimating] = useState(false);
  const [showSampleDrawer, setShowSampleDrawer] = useState(false);

  // Fetch available tags
  const { data: tagsData } = useQuery({
    queryKey: ['broadcast-tags'],
    queryFn: broadcastApi.tags,
  });
  const availableTags = tagsData?.tags ?? ['vip', 'lead_quente', 'cliente', 'abandono_carrinho', 'oraculo'];

  // Current segment filters object
  const currentFilters = useMemo(() => {
    const filters: Record<string, unknown> = {
      include_opted_out: !excludeOptedOut,
      has_phone: true,
      anti_ban_delay_seconds: antiBanDelaySeconds,
    };
    if (selectedTags.length > 0) {
      filters.tags = selectedTags;
    }
    if (scoreBand !== 'all') {
      filters.score_band = [scoreBand];
    }
    return filters;
  }, [selectedTags, scoreBand, excludeOptedOut, antiBanDelaySeconds]);

  // Debounced Audience Estimation
  useEffect(() => {
    let active = true;
    setIsEstimating(true);
    const timer = setTimeout(async () => {
      try {
        const res = await broadcastApi.previewSegment(currentFilters);
        if (active) {
          setAudienceCount(res.total_matching);
          setAudienceSample(res.sample || []);
          setIsEstimating(false);
        }
      } catch {
        if (active) setIsEstimating(false);
      }
    }, 400);

    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [currentFilters]);

  // Submit Mutation
  const createMut = useMutation({
    mutationFn: (asDraft: boolean) =>
      broadcastApi.create({
        title: name,
        message_text: message,
        message_media_url: mediaUrl ? mediaUrl : null,
        message_media_type: mediaUrl ? mediaType : null,
        segment_filters: currentFilters,
        status: asDraft ? 'draft' : sendMode === 'scheduled' && scheduledAt ? 'scheduled' : 'draft',
        scheduled_at: !asDraft && sendMode === 'scheduled' && scheduledAt ? new Date(scheduledAt).toISOString() : undefined,
      }),
    onSuccess: (res, asDraft) => {
      if (!asDraft && sendMode === 'immediate') {
        // Disparar imediatamente se solicitado
        broadcastApi.send(res.id).then(() => {
          toast.success('🚀 Campanha criada e disparo iniciado com sucesso!');
          onCreated();
        }).catch(() => {
          toast.success('Campanha criada como rascunho. Inicie o disparo quando desejar.');
          onCreated();
        });
      } else {
        toast.success(
          asDraft
            ? 'Campanha salva como rascunho!'
            : `Campanha agendada com sucesso para ${new Date(scheduledAt).toLocaleString('pt-BR')}!`
        );
        onCreated();
      }
    },
    onError: handleApiError('Erro ao criar campanha'),
  });

  const toggleTag = (tag: string) => {
    setSelectedTags(prev => (prev.includes(tag) ? prev.filter(t => t !== tag) : [...prev, tag]));
  };

  const addCustomTag = () => {
    const clean = customTagInput.trim().toLowerCase();
    if (clean && !selectedTags.includes(clean)) {
      setSelectedTags(prev => [...prev, clean]);
      setCustomTagInput('');
    }
  };

  const insertVariable = (varName: string) => {
    setMessage(prev => `${prev} {${varName}} `);
  };

  // Live formatted WhatsApp preview text
  const previewText = useMemo(() => {
    if (!message) return 'Olá! Digite sua mensagem ao lado para visualizar a prévia aqui em tempo real...';
    return message
      .replace(/{nome}/gi, 'Maria Eduarda')
      .replace(/{primeiro_nome}/gi, 'Maria')
      .replace(/{telefone}/gi, '(11) 98765-4321')
      .replace(/{signo}/gi, 'Leão')
      .replace(/{score}/gi, 'Quente');
  }, [message]);

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-3 md:p-6 overflow-y-auto animate-in fade-in duration-200">
      <div className="bg-bg-surface border border-border rounded-3xl max-w-4xl w-full flex flex-col max-h-[92vh] shadow-2xl overflow-hidden my-auto">
        {/* Stepper Header */}
        <div className="p-5 md:p-6 border-b border-border bg-bg-surface/90">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-accent-amethyst/15 flex items-center justify-center text-accent-amethyst font-black text-sm">
                {step}
              </div>
              <div>
                <h2 className="text-lg font-black tracking-tight">Nova Campanha de Broadcast</h2>
                <p className="text-xs text-secondary">
                  {step === 1 && 'Etapa 1 de 4 — Defina a audiência e filtros de segmentação'}
                  {step === 2 && 'Etapa 2 de 4 — Redija a mensagem e veja o preview do WhatsApp'}
                  {step === 3 && 'Etapa 3 de 4 — Configure agendamento e proteção anti-ban'}
                  {step === 4 && 'Etapa 4 de 4 — Revisão pré-voo e confirmação do disparo'}
                </p>
              </div>
            </div>
            <button onClick={onClose} className="p-2 hover:bg-bg-primary rounded-xl text-secondary hover:text-white transition-all">
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Stepper Bar */}
          <div className="grid grid-cols-4 gap-2">
            {[
              { num: 1, label: '1. Audiência' },
              { num: 2, label: '2. Mensagem' },
              { num: 3, label: '3. Anti-Ban' },
              { num: 4, label: '4. Revisão' },
            ].map(s => (
              <div
                key={s.num}
                className={`h-1.5 rounded-full transition-all ${
                  step >= s.num ? 'bg-accent-amethyst' : 'bg-bg-primary border border-border/40'
                }`}
              />
            ))}
          </div>
        </div>

        {/* Wizard Step Body */}
        <div className="p-6 overflow-y-auto flex-1 space-y-6">
          {/* ══════════════════════════════════════════════════════════════════
              PASSO 1: AUDIÊNCIA & SEGMENTAÇÃO
              ══════════════════════════════════════════════════════════════════ */}
          {step === 1 && (
            <div className="space-y-6">
              {/* Audience Estimator Card */}
              <div className="p-5 rounded-2xl bg-gradient-to-r from-accent-amethyst/15 via-accent-amethyst/5 to-transparent border border-accent-amethyst/30 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 rounded-2xl bg-accent-amethyst/20 flex items-center justify-center text-accent-amethyst">
                    <Sparkles className="w-6 h-6" />
                  </div>
                  <div>
                    <div className="text-[10px] font-black uppercase tracking-widest text-accent-amethyst">
                      Estimativa de Destinatários
                    </div>
                    <div className="text-2xl font-black text-white flex items-center gap-2">
                      {isEstimating ? (
                        <span className="text-sm font-normal text-secondary animate-pulse">Calculando base...</span>
                      ) : (
                        <span>{audienceCount ?? 0} leads qualificados</span>
                      )}
                    </div>
                  </div>
                </div>

                {audienceSample.length > 0 && (
                  <button
                    onClick={() => setShowSampleDrawer(!showSampleDrawer)}
                    className="px-4 py-2 bg-bg-surface hover:bg-bg-surface/80 border border-border rounded-xl text-xs font-bold text-secondary hover:text-white transition-all self-start sm:self-center"
                  >
                    {showSampleDrawer ? 'Ocultar amostra' : 'Ver amostra de contatos'}
                  </button>
                )}
              </div>

              {/* Sample contacts accordion */}
              {showSampleDrawer && audienceSample.length > 0 && (
                <div className="p-4 rounded-2xl bg-bg-primary/50 border border-border space-y-2 animate-in fade-in">
                  <div className="text-[10px] font-black uppercase tracking-widest text-secondary mb-2">
                    Primeiros contatos que receberão o disparo:
                  </div>
                  {audienceSample.map(lead => (
                    <div key={lead.id} className="flex items-center justify-between text-xs py-1 border-b border-border/30 last:border-0">
                      <span className="font-bold text-white">{lead.nome || 'Lead sem nome'}</span>
                      <span className="font-mono text-secondary">{lead.telefone}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Tags Filter */}
              <div className="space-y-2">
                <label className="text-[10px] font-black uppercase tracking-widest text-secondary block">
                  Filtrar por Tags da Base
                </label>
                <div className="flex flex-wrap gap-2">
                  {availableTags.map(tag => {
                    const active = selectedTags.includes(tag);
                    return (
                      <button
                        key={tag}
                        type="button"
                        onClick={() => toggleTag(tag)}
                        className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 ${
                          active
                            ? 'bg-accent-amethyst text-white shadow-sm'
                            : 'bg-bg-primary border border-border text-secondary hover:text-white'
                        }`}
                      >
                        {active && <Check className="w-3 h-3" />} #{tag}
                      </button>
                    );
                  })}
                </div>

                {/* Custom tag input */}
                <div className="flex items-center gap-2 pt-2 max-w-sm">
                  <input
                    type="text"
                    placeholder="Adicionar outra tag..."
                    value={customTagInput}
                    onChange={e => setCustomTagInput(e.target.value)}
                    onKeyDown={e => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        addCustomTag();
                      }
                    }}
                    className="flex-1 px-3 py-1.5 bg-bg-primary border border-border rounded-xl text-xs focus:border-accent-amethyst outline-none"
                  />
                  <button
                    type="button"
                    onClick={addCustomTag}
                    className="px-3 py-1.5 bg-bg-surface hover:bg-bg-surface/80 border border-border rounded-xl text-xs font-bold text-white"
                  >
                    + Adicionar
                  </button>
                </div>
              </div>

              {/* Commercial Score Filter */}
              <div className="space-y-2">
                <label className="text-[10px] font-black uppercase tracking-widest text-secondary block">
                  Score Comercial do Lead
                </label>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {[
                    { id: 'all', label: 'Todos os Leads' },
                    { id: 'hot', label: '🔥 Quentes (Alta Intenção)' },
                    { id: 'warm', label: '⚡ Mornos (Engajados)' },
                    { id: 'cold', label: '❄️ Frios (Reengajamento)' },
                  ].map(b => (
                    <button
                      key={b.id}
                      type="button"
                      onClick={() => setScoreBand(b.id)}
                      className={`p-3 rounded-xl text-xs font-bold border transition-all text-left ${
                        scoreBand === b.id
                          ? 'bg-accent-amethyst/15 border-accent-amethyst text-white'
                          : 'bg-bg-primary border-border text-secondary hover:text-white'
                      }`}
                    >
                      {b.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Opt-out Protection Checkbox */}
              <div className="pt-2 space-y-2">
                <label className="flex items-center gap-3 cursor-pointer p-3 rounded-xl bg-bg-primary/40 border border-border/50">
                  <input
                    type="checkbox"
                    checked={excludeOptedOut}
                    onChange={e => setExcludeOptedOut(e.target.checked)}
                    className="w-4 h-4 accent-accent-amethyst rounded"
                  />
                  <div>
                    <div className="text-xs font-bold text-white">Excluir descadastrados (opted-out)</div>
                    <div className="text-[11px] text-secondary">
                      Garante conformidade e evita que leads que pediram para sair recebam mensagens.
                    </div>
                  </div>
                </label>
              </div>
            </div>
          )}

          {/* ══════════════════════════════════════════════════════════════════
              PASSO 2: MENSAGEM & PREVIEW REAL NO WHATSAPP
              ══════════════════════════════════════════════════════════════════ */}
          {step === 2 && (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              {/* Left Column: Form */}
              <div className="lg:col-span-7 space-y-4">
                <div>
                  <label className="text-[10px] font-black uppercase tracking-widest text-secondary block mb-1.5">
                    Nome da Campanha
                  </label>
                  <input
                    type="text"
                    placeholder="Ex: Lançamento VIP de Tarot Junho"
                    value={name}
                    onChange={e => setName(e.target.value)}
                    className="w-full px-4 py-2.5 bg-bg-primary border border-border rounded-xl text-sm focus:border-accent-amethyst outline-none font-medium"
                  />
                </div>

                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <label className="text-[10px] font-black uppercase tracking-widest text-secondary block">
                      Mensagem do WhatsApp
                    </label>
                    <span className="text-[10px] text-secondary font-mono">{message.length} caracteres</span>
                  </div>
                  <textarea
                    rows={6}
                    placeholder="Olá {nome}! Tenho uma novidade especial sobre a sua previsão..."
                    value={message}
                    onChange={e => setMessage(e.target.value)}
                    className="w-full p-4 bg-bg-primary border border-border rounded-2xl text-sm focus:border-accent-amethyst outline-none resize-none font-medium leading-relaxed"
                  />
                </div>

                {/* Variable Pills */}
                <div>
                  <div className="text-[10px] font-black uppercase tracking-widest text-secondary mb-2">
                    Inserir Variáveis Personalizadas:
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {[
                      { varName: 'nome', label: '{nome}' },
                      { varName: 'primeiro_nome', label: '{primeiro_nome}' },
                      { varName: 'telefone', label: '{telefone}' },
                      { varName: 'signo', label: '{signo}' },
                    ].map(v => (
                      <button
                        key={v.varName}
                        type="button"
                        onClick={() => insertVariable(v.varName)}
                        className="px-2.5 py-1 rounded-lg bg-accent-amethyst/10 hover:bg-accent-amethyst/20 border border-accent-amethyst/30 text-accent-amethyst font-mono text-xs font-bold transition-all"
                      >
                        + {v.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Media Attachment */}
                <div className="pt-2 space-y-2">
                  <label className="text-[10px] font-black uppercase tracking-widest text-secondary block">
                    Anexar Mídia Opcional (URL Pública)
                  </label>
                  <div className="flex gap-2">
                    <select
                      value={mediaType}
                      onChange={e => setMediaType(e.target.value as 'image' | 'video' | 'document')}
                      className="px-3 py-2 bg-bg-primary border border-border rounded-xl text-xs font-bold outline-none"
                    >
                      <option value="image">Imagem (JPG/PNG)</option>
                      <option value="video">Vídeo (MP4)</option>
                      <option value="document">Documento (PDF)</option>
                    </select>
                    <input
                      type="url"
                      placeholder="https://exemplo.com/banner.jpg"
                      value={mediaUrl}
                      onChange={e => setMediaUrl(e.target.value)}
                      className="flex-1 px-3 py-2 bg-bg-primary border border-border rounded-xl text-xs focus:border-accent-amethyst outline-none font-mono"
                    />
                  </div>
                </div>
              </div>

              {/* Right Column: WhatsApp Mockup Preview */}
              <div className="lg:col-span-5 flex flex-col items-center">
                <div className="w-full max-w-[290px] bg-[#121b22] border-4 border-[#2a3942] rounded-[38px] shadow-2xl p-3 flex flex-col relative overflow-hidden">
                  {/* Speaker & notch */}
                  <div className="w-20 h-3.5 bg-[#2a3942] rounded-full mx-auto mb-2" />

                  {/* WhatsApp Top Bar */}
                  <div className="flex items-center gap-2.5 pb-2 border-b border-[#202c33] px-1">
                    <div className="w-7 h-7 rounded-full bg-emerald-600 flex items-center justify-center text-[10px] font-bold text-white">
                      OA
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-[11px] font-bold text-[#e9edef] truncate">Acássia / Atendente</div>
                      <div className="text-[9px] text-emerald-400">online</div>
                    </div>
                  </div>

                  {/* Chat Area */}
                  <div className="py-4 px-1 min-h-[260px] flex flex-col justify-end space-y-2">
                    {/* Media Preview inside bubble if present */}
                    <div className="bg-[#005c4b] text-[#e9edef] p-3 rounded-2xl rounded-tr-none shadow-md space-y-2 text-xs leading-relaxed max-w-[95%] self-end">
                      {mediaUrl && (
                        <div className="w-full h-28 rounded-lg bg-black/30 flex items-center justify-center overflow-hidden border border-white/10">
                          {mediaType === 'image' ? (
                            <img src={mediaUrl} alt="Preview" className="w-full h-full object-cover" onError={e => (e.currentTarget.style.display = 'none')} />
                          ) : (
                            <div className="text-[11px] text-white/70 flex items-center gap-1.5">
                              <FileText className="w-4 h-4" /> Mídia anexada
                            </div>
                          )}
                        </div>
                      )}
                      <p className="whitespace-pre-wrap break-words">{previewText}</p>
                      <div className="flex items-center justify-end gap-1 text-[9px] text-white/60">
                        <span>14:32</span>
                        <span className="text-sky-300 font-bold">✓✓</span>
                      </div>
                    </div>
                  </div>

                  {/* Bottom Home Indicator */}
                  <div className="w-24 h-1 bg-[#2a3942] rounded-full mx-auto mt-2" />
                </div>
                <span className="text-[10px] text-secondary mt-2 flex items-center gap-1">
                  <Smartphone className="w-3 h-3" /> Prévia ao vivo no celular
                </span>
              </div>
            </div>
          )}

          {/* ══════════════════════════════════════════════════════════════════
              PASSO 3: AGENDAMENTO & PROTEÇÃO ANTI-BAN
              ══════════════════════════════════════════════════════════════════ */}
          {step === 3 && (
            <div className="space-y-6">
              {/* Send Mode Choice */}
              <div className="space-y-2">
                <label className="text-[10px] font-black uppercase tracking-widest text-secondary block">
                  Momento do Disparo
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <button
                    type="button"
                    onClick={() => setSendMode('immediate')}
                    className={`p-5 rounded-2xl border transition-all text-left flex items-start gap-3 ${
                      sendMode === 'immediate'
                        ? 'bg-accent-amethyst/15 border-accent-amethyst text-white shadow-md'
                        : 'bg-bg-primary border-border text-secondary hover:text-white'
                    }`}
                  >
                    <div className="w-9 h-9 rounded-xl bg-accent-amethyst/20 flex items-center justify-center text-accent-amethyst shrink-0">
                      <Send className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="font-bold text-sm text-white">Disparar Imediatamente</div>
                      <div className="text-xs text-secondary mt-1">
                        Inicia a fila de envio no WhatsApp assim que você confirmar a campanha.
                      </div>
                    </div>
                  </button>

                  <button
                    type="button"
                    onClick={() => setSendMode('scheduled')}
                    className={`p-5 rounded-2xl border transition-all text-left flex items-start gap-3 ${
                      sendMode === 'scheduled'
                        ? 'bg-accent-amethyst/15 border-accent-amethyst text-white shadow-md'
                        : 'bg-bg-primary border-border text-secondary hover:text-white'
                    }`}
                  >
                    <div className="w-9 h-9 rounded-xl bg-blue-500/20 flex items-center justify-center text-blue-400 shrink-0">
                      <CalendarClock className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="font-bold text-sm text-white">Agendar Data & Horário</div>
                      <div className="text-xs text-secondary mt-1">
                        Programe o disparo para o momento exato de maior engajamento da sua base.
                      </div>
                    </div>
                  </button>
                </div>
              </div>

              {/* Scheduled Datetime Picker */}
              {sendMode === 'scheduled' && (
                <div className="p-4 rounded-2xl bg-bg-primary/50 border border-border space-y-2 animate-in fade-in">
                  <label className="text-[10px] font-black uppercase tracking-widest text-secondary block">
                    Data e Horário de Execução
                  </label>
                  <input
                    type="datetime-local"
                    value={scheduledAt}
                    onChange={e => setScheduledAt(e.target.value)}
                    className="w-full max-w-sm px-4 py-2.5 bg-bg-surface border border-border rounded-xl text-sm font-medium text-white outline-none focus:border-accent-amethyst"
                  />
                  <div className="text-[11px] text-secondary">
                    O cron job do sistema disparará a campanha automaticamente no horário agendado.
                  </div>
                </div>
              )}

              {/* Meta WhatsApp Anti-Ban Shield */}
              <div className="p-5 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 space-y-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-indigo-500/20 flex items-center justify-center text-indigo-400">
                    <ShieldCheck className="w-5 h-5" />
                  </div>
                  <div>
                    <h4 className="font-bold text-sm text-white">Proteção Anti-Ban Meta (Rate Limiting)</h4>
                    <p className="text-xs text-secondary">
                      Controla o intervalo inteligente entre cada mensagem para proteger seu número WhatsApp contra bloqueios.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  {[
                    { sec: 5, label: '5 segundos (Recomendado Meta)', desc: 'Equilíbrio ideal entre velocidade e segurança.' },
                    { sec: 2, label: '2 segundos (Rápido)', desc: 'Para números antigos com alto volume diário.' },
                    { sec: 10, label: '10 segundos (Ultra Seguro)', desc: 'Recomendado para chips novos ou reativação.' },
                  ].map(opt => (
                    <button
                      key={opt.sec}
                      type="button"
                      onClick={() => setAntiBanDelaySeconds(opt.sec)}
                      className={`p-3.5 rounded-xl border text-left transition-all ${
                        antiBanDelaySeconds === opt.sec
                          ? 'bg-indigo-500/20 border-indigo-500 text-white'
                          : 'bg-bg-primary border-border text-secondary hover:text-white'
                      }`}
                    >
                      <div className="font-bold text-xs text-white">{opt.label}</div>
                      <div className="text-[10px] text-secondary mt-1">{opt.desc}</div>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ══════════════════════════════════════════════════════════════════
              PASSO 4: REVISÃO PRÉ-VOO & CONFIRMAÇÃO
              ══════════════════════════════════════════════════════════════════ */}
          {step === 4 && (
            <div className="space-y-6">
              <div className="p-5 rounded-2xl bg-bg-primary/50 border border-border space-y-4">
                <h3 className="font-black text-sm uppercase tracking-wider text-accent-amethyst">
                  Checklist Pré-Voo da Campanha
                </h3>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                  <div>
                    <span className="text-secondary block font-medium">Nome da Campanha:</span>
                    <strong className="text-white text-sm font-bold">{name || 'Sem título'}</strong>
                  </div>
                  <div>
                    <span className="text-secondary block font-medium">Base de Destinatários:</span>
                    <strong className="text-emerald-400 text-sm font-bold">{audienceCount ?? 0} contatos qualificados</strong>
                  </div>
                  <div>
                    <span className="text-secondary block font-medium">Modo de Envio:</span>
                    <strong className="text-white font-bold">
                      {sendMode === 'immediate'
                        ? '⚡ Imediato'
                        : `📅 Agendado para ${scheduledAt ? new Date(scheduledAt).toLocaleString('pt-BR') : 'Data não definida'}`}
                    </strong>
                  </div>
                  <div>
                    <span className="text-secondary block font-medium">Intervalo Anti-Ban:</span>
                    <strong className="text-indigo-400 font-bold">{antiBanDelaySeconds} segundos por lead</strong>
                  </div>
                </div>

                <div className="pt-3 border-t border-border/50">
                  <span className="text-secondary block text-xs font-medium mb-1">Prévia da Mensagem:</span>
                  <div className="p-3.5 rounded-xl bg-bg-surface border border-border text-xs text-secondary font-mono whitespace-pre-wrap">
                    {message}
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-3 p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs">
                <AlertTriangle className="w-5 h-5 shrink-0" />
                <span>
                  Após o início, as mensagens serão enviadas de forma sequencial com espaçamento de {antiBanDelaySeconds}s. Você poderá pausar ou auditar a fila a qualquer momento.
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Wizard Footer */}
        <div className="p-5 md:p-6 border-t border-border bg-bg-surface flex items-center justify-between">
          <div>
            {step > 1 && (
              <button
                type="button"
                onClick={() => setStep((prev => (prev - 1) as 1 | 2 | 3 | 4))}
                className="flex items-center gap-1.5 px-4 py-2.5 bg-bg-primary hover:bg-bg-primary/80 border border-border rounded-xl text-xs font-bold text-white transition-all"
              >
                <ChevronLeft className="w-4 h-4" /> Voltar
              </button>
            )}
          </div>

          <div className="flex items-center gap-3">
            {step === 4 && (
              <button
                type="button"
                onClick={() => createMut.mutate(true)}
                disabled={createMut.isPending}
                className="px-4 py-2.5 bg-bg-primary hover:bg-bg-primary/80 border border-border rounded-xl text-xs font-bold text-secondary hover:text-white transition-all"
              >
                Salvar Rascunho
              </button>
            )}

            {step < 4 ? (
              <button
                type="button"
                onClick={() => {
                  if (step === 2 && (!name.trim() || !message.trim())) {
                    toast.error('Preencha o nome da campanha e a mensagem.');
                    return;
                  }
                  setStep((prev => (prev + 1) as 1 | 2 | 3 | 4));
                }}
                className="flex items-center gap-1.5 px-5 py-2.5 bg-accent-amethyst hover:bg-accent-amethyst/90 text-white rounded-xl text-xs font-black uppercase tracking-wider transition-all shadow-md shadow-accent-amethyst/20"
              >
                Avançar <ChevronRight className="w-4 h-4" />
              </button>
            ) : (
              <button
                type="button"
                onClick={() => createMut.mutate(false)}
                disabled={createMut.isPending || !name.trim() || !message.trim()}
                className="flex items-center gap-2 px-6 py-2.5 bg-accent-amethyst hover:bg-accent-amethyst/90 disabled:opacity-40 text-white rounded-xl text-xs font-black uppercase tracking-widest transition-all shadow-lg shadow-accent-amethyst/25"
              >
                {createMut.isPending ? (
                  'Processando...'
                ) : sendMode === 'scheduled' ? (
                  <>
                    <CalendarClock className="w-4 h-4" /> Confirmar Agendamento
                  </>
                ) : (
                  <>
                    <Send className="w-4 h-4" /> Iniciar Disparo
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
