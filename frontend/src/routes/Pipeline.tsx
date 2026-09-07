import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Kanban, Users, TrendingUp, Sparkles, Tag, Zap,
  GripVertical, MessageSquare, Star, ChevronRight, Play,
  RefreshCw, Search, Filter, BarChart3, DollarSign,
  ListChecks, Target, Clock, Percent, Activity
} from 'lucide-react';
import { api } from '../api/client';
import { toast } from '../lib/toast';

type Stage = { key: string; label: string; emoji: string; color: string };
type LeadCard = {
  id: number; nome: string; telefone: string; signo: string | null;
  score_value: number; score_band: string; tags: string[];
  spiritual_category: string | null; pipeline_stage: string;
  convertido: boolean; bot_pausado: boolean; msg_count: number;
  deal_value: number; win_probability: number;
  engagement_level: string; preferred_hour: number | null;
  last_msg: string | null; last_msg_at: string | null; created_at: string | null;
};
type Recipe = {
  id: string; name: string; emoji: string; description: string;
  trigger: string; steps: { delay: string; action: string; text?: string }[];
  category: string;
};
type ACDash = {
  tasks_pending: number; tasks_overdue: number;
  conversions_30d: number; revenue_30d: number;
  pipeline_value: number; engagement: Record<string, number>;
  widgets_captured: number;
};

type Tab = 'kanban' | 'recipes' | 'stats' | 'intelligence';

const BAND_COLORS: Record<string, string> = {
  hot: 'bg-rose-500/20 text-rose-400 border-rose-500/30',
  warm: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  cold: 'bg-sky-500/20 text-sky-400 border-sky-500/30',
};

export default function Pipeline() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<Tab>('kanban');
  const [search, setSearch] = useState('');
  const [draggedLead, setDraggedLead] = useState<LeadCard | null>(null);

  const { data: boardData, isLoading } = useQuery({
    queryKey: ['pipeline-board'],
    queryFn: () => api.get<{
      board: Record<string, LeadCard[]>;
      stages: Stage[];
      counts: Record<string, number>;
      total: number;
    }>('/saas/pipeline/board'),
  });

  const { data: recipesData } = useQuery({
    queryKey: ['pipeline-recipes'],
    queryFn: () => api.get<{ recipes: Recipe[]; categories: string[] }>('/saas/pipeline/recipes'),
  });

  const { data: statsData } = useQuery({
    queryKey: ['pipeline-stats'],
    queryFn: () => api.get<{
      counts: Record<string, number>; total: number; converted: number;
      lost: number; conversion_rate: number; new_last_30d: number;
      avg_score_by_stage: Record<string, number>;
    }>('/saas/pipeline/stats'),
    enabled: tab === 'stats',
  });

  const { data: acDash } = useQuery({
    queryKey: ['ac-dashboard'],
    queryFn: () => api.get<ACDash>('/saas/ac/dashboard'),
    enabled: tab === 'intelligence',
  });

  const { data: forecastData } = useQuery({
    queryKey: ['ac-forecast'],
    queryFn: () => api.get<{
      by_stage: Record<string, { count: number; raw_value: number; weighted_value: number }>;
      total_pipeline_value: number; weighted_forecast: number; total_leads: number;
    }>('/saas/ac/forecast'),
    enabled: tab === 'intelligence',
  });

  const { data: convData } = useQuery({
    queryKey: ['ac-conversions'],
    queryFn: () => api.get<{
      by_source: { source: string; type: string; count: number; value: number }[];
      total_conversions: number; total_value: number;
    }>('/saas/ac/conversions?days=30'),
    enabled: tab === 'intelligence',
  });

  const moveMut = useMutation({
    mutationFn: (params: { lead_id: number; stage: string }) =>
      api.post('/saas/pipeline/move', params),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['pipeline-board'] });
      qc.invalidateQueries({ queryKey: ['pipeline-stats'] });
      toast.success('Lead movido!');
    },
  });

  const autoTagMut = useMutation({
    mutationFn: () => api.post<{ leads_tagged: number; total_checked: number }>('/saas/pipeline/auto-tag', {}),
    onSuccess: (res: { leads_tagged: number; total_checked: number }) => {
      qc.invalidateQueries({ queryKey: ['pipeline-board'] });
      toast.success(`${res.leads_tagged} leads auto-tagged de ${res.total_checked} verificados`);
    },
  });

  const engRecalc = useMutation({
    mutationFn: () => api.post('/saas/ac/engagement/recalc', {}),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['pipeline-board'] });
      qc.invalidateQueries({ queryKey: ['ac-dashboard'] });
      toast.success('Engagement recalculado!');
    },
  });

  const winRecalc = useMutation({
    mutationFn: () => api.post('/saas/ac/win-probability/recalc', {}),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['pipeline-board'] });
      toast.success('Win Probability atualizado!');
    },
  });

  const stages = boardData?.stages || [];
  const board = boardData?.board || {};
  const total = boardData?.total || 0;

  // Drag handlers
  const handleDragStart = (lead: LeadCard) => setDraggedLead(lead);
  const handleDragOver = (e: React.DragEvent) => { e.preventDefault(); e.dataTransfer.dropEffect = 'move'; };
  const handleDrop = (stageKey: string) => {
    if (draggedLead && draggedLead.pipeline_stage !== stageKey) {
      moveMut.mutate({ lead_id: draggedLead.id, stage: stageKey });
    }
    setDraggedLead(null);
  };

  // Filter by search
  const filterLeads = (leads: LeadCard[]) =>
    search ? leads.filter(l => l.nome.toLowerCase().includes(search.toLowerCase()) || l.telefone.includes(search)) : leads;

  return (
    <div className="px-8 py-8 max-w-[1800px] mx-auto min-h-screen">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/30">
              <Kanban className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="font-display text-3xl text-primary tracking-tight">Pipeline</h1>
              <p className="text-xs text-secondary">{total} leads no funil</p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => autoTagMut.mutate()}
            disabled={autoTagMut.isPending}
            className="flex items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-amber-500 to-orange-500 text-white rounded-xl text-xs font-bold shadow-lg shadow-amber-500/20 hover:scale-105 active:scale-95 transition-all"
          >
            {autoTagMut.isPending ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Tag className="w-4 h-4" />}
            Auto-Tag IA
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 bg-bg-sidebar p-1 rounded-2xl border border-border mb-6 w-fit">
        {([
          { key: 'kanban', label: 'Kanban', icon: Kanban },
          { key: 'recipes', label: 'Receitas', icon: Zap },
          { key: 'stats', label: 'Métricas', icon: BarChart3 },
          { key: 'intelligence', label: 'Inteligência', icon: Activity },
        ] as const).map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold transition-all ${
              tab === t.key
                ? 'bg-bg-surface text-primary shadow-sm border border-border'
                : 'text-secondary hover:text-primary'
            }`}
          >
            <t.icon className="w-4 h-4" />
            {t.label}
          </button>
        ))}
      </div>

      {/* TAB: KANBAN */}
      {tab === 'kanban' && (
        <>
          {/* Search bar */}
          <div className="relative mb-6 max-w-sm">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-secondary" />
            <input
              type="text"
              placeholder="Buscar lead..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 bg-bg-surface border border-border rounded-xl text-sm text-primary placeholder:text-secondary/50 focus:outline-none focus:border-indigo-500 transition-all"
            />
          </div>

          {isLoading ? (
            <div className="flex items-center justify-center py-20">
              <RefreshCw className="w-8 h-8 text-indigo-500 animate-spin" />
            </div>
          ) : (
            <div className="flex gap-4 overflow-x-auto pb-4 scrollbar-hide">
              {stages.map(stage => {
                const leads = filterLeads(board[stage.key] || []);
                const isDragOver = draggedLead && draggedLead.pipeline_stage !== stage.key;

                return (
                  <div
                    key={stage.key}
                    className={`flex-shrink-0 w-[280px] bg-bg-sidebar rounded-2xl border transition-all ${
                      isDragOver ? 'border-indigo-500/50 shadow-lg shadow-indigo-500/10' : 'border-border'
                    }`}
                    onDragOver={handleDragOver}
                    onDrop={() => handleDrop(stage.key)}
                  >
                    {/* Column Header */}
                    <div className="p-4 border-b border-border">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="text-lg">{stage.emoji}</span>
                          <span className="text-xs font-bold text-primary">{stage.label}</span>
                        </div>
                        <span
                          className="text-[10px] font-bold px-2 py-1 rounded-lg"
                          style={{ backgroundColor: stage.color + '20', color: stage.color }}
                        >
                          {leads.length}
                        </span>
                      </div>
                    </div>

                    {/* Cards */}
                    <div className="p-2 space-y-2 max-h-[600px] overflow-y-auto scrollbar-hide">
                      {leads.length === 0 ? (
                        <div className="py-8 text-center text-xs text-secondary/50 italic">
                          Nenhum lead
                        </div>
                      ) : (
                        leads.map(lead => (
                          <div
                            key={lead.id}
                            draggable
                            onDragStart={() => handleDragStart(lead)}
                            onDragEnd={() => setDraggedLead(null)}
                            className={`p-3 bg-bg-surface rounded-xl border border-border cursor-grab active:cursor-grabbing hover:border-indigo-500/30 transition-all group ${
                              draggedLead?.id === lead.id ? 'opacity-40 scale-95' : ''
                            }`}
                          >
                            {/* Lead name + score */}
                            <div className="flex items-center justify-between mb-2">
                              <div className="flex items-center gap-2 min-w-0">
                                <GripVertical className="w-3 h-3 text-secondary/30 group-hover:text-secondary flex-shrink-0" />
                                <span className="text-sm font-bold text-primary truncate">{lead.nome}</span>
                              </div>
                              <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded border ${BAND_COLORS[lead.score_band] || BAND_COLORS.cold}`}>
                                {lead.score_value}
                              </span>
                            </div>

                            {/* Tags */}
                            {lead.tags.length > 0 && (
                              <div className="flex flex-wrap gap-1 mb-2">
                                {lead.tags.slice(0, 3).map(tag => (
                                  <span key={tag} className="text-[8px] font-bold px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                                    {tag}
                                  </span>
                                ))}
                                {lead.tags.length > 3 && (
                                  <span className="text-[8px] text-secondary">+{lead.tags.length - 3}</span>
                                )}
                              </div>
                            )}

                            {/* Last message preview */}
                            {lead.last_msg && (
                              <div className="text-[10px] text-secondary/70 line-clamp-1 mb-1">
                                💬 {lead.last_msg}
                              </div>
                            )}

                            {/* Footer with deal value + win prob */}
                            <div className="flex items-center justify-between text-[9px] text-secondary/50">
                              <div className="flex items-center gap-2">
                                {lead.signo && <span>♈ {lead.signo}</span>}
                                <span className="flex items-center gap-0.5">
                                  <MessageSquare className="w-2.5 h-2.5" /> {lead.msg_count}
                                </span>
                              </div>
                              <div className="flex items-center gap-2">
                                {(lead.deal_value > 0) && (
                                  <span className="text-emerald-400 font-bold">R${lead.deal_value}</span>
                                )}
                                {(lead.win_probability > 0) && (
                                  <span className={`font-bold ${lead.win_probability >= 60 ? 'text-emerald-400' : lead.win_probability >= 30 ? 'text-amber-400' : 'text-secondary/50'}`}>
                                    {lead.win_probability}%
                                  </span>
                                )}
                              </div>
                            </div>

                            {/* Engagement badge */}
                            {lead.engagement_level !== 'unknown' && (
                              <div className="mt-1.5">
                                <span className={`text-[8px] font-bold px-1.5 py-0.5 rounded border ${
                                  lead.engagement_level === 'superfan' ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' :
                                  lead.engagement_level === 'engaged' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                                  lead.engagement_level === 'idle' ? 'bg-amber-500/10 text-amber-400 border-amber-500/20' :
                                  'bg-gray-500/10 text-gray-400 border-gray-500/20'
                                }`}>
                                  {lead.engagement_level === 'superfan' ? '🔥 Superfan' :
                                   lead.engagement_level === 'engaged' ? '✅ Engajado' :
                                   lead.engagement_level === 'idle' ? '💤 Idle' : '❌ Inativo'}
                                </span>
                              </div>
                            )}
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}

      {/* TAB: RECIPES */}
      {tab === 'recipes' && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {(recipesData?.recipes || []).map(recipe => (
            <div
              key={recipe.id}
              className="bg-bg-surface border border-border rounded-2xl p-5 hover:border-indigo-500/30 transition-all group"
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <span className="text-2xl">{recipe.emoji}</span>
                  <div>
                    <h3 className="font-bold text-sm text-primary">{recipe.name}</h3>
                    <span className="text-[9px] font-bold uppercase tracking-widest text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded">
                      {recipe.category}
                    </span>
                  </div>
                </div>
              </div>

              <p className="text-xs text-secondary mb-4">{recipe.description}</p>

              <div className="text-[10px] text-secondary/70 mb-3">
                <span className="font-bold text-primary">Trigger:</span> {recipe.trigger}
              </div>

              {/* Steps preview */}
              <div className="space-y-1.5 mb-4">
                {recipe.steps.slice(0, 3).map((step, i) => (
                  <div key={i} className="flex items-start gap-2 text-[10px]">
                    <div className="w-5 h-5 rounded-full bg-indigo-500/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                      <span className="text-indigo-400 font-bold text-[8px]">{i + 1}</span>
                    </div>
                    <div>
                      <span className="text-secondary font-medium">+{step.delay}</span>
                      {step.text && (
                        <span className="text-primary ml-1 line-clamp-1">{step.text.substring(0, 60)}...</span>
                      )}
                      {step.action === 'tarot_reading' && (
                        <span className="text-indigo-400 ml-1">🔮 Tiragem automática</span>
                      )}
                    </div>
                  </div>
                ))}
                {recipe.steps.length > 3 && (
                  <div className="text-[9px] text-secondary/50 ml-7">+{recipe.steps.length - 3} mais passos</div>
                )}
              </div>

              <button className="w-full py-2.5 bg-gradient-to-r from-indigo-500 to-purple-600 text-white rounded-xl text-xs font-bold opacity-0 group-hover:opacity-100 transition-all flex items-center justify-center gap-2 shadow-lg shadow-indigo-500/20">
                <Play className="w-3 h-3" />
                Ativar Receita
              </button>
            </div>
          ))}
        </div>
      )}

      {/* TAB: STATS */}
      {tab === 'stats' && statsData && (
        <div className="space-y-6">
          {/* KPIs */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: 'Total no Funil', value: statsData.total, icon: Users, color: 'from-indigo-500 to-purple-600' },
              { label: 'Convertidos', value: statsData.converted, icon: Star, color: 'from-emerald-500 to-green-600' },
              { label: 'Taxa Conversão', value: `${statsData.conversion_rate}%`, icon: TrendingUp, color: 'from-amber-500 to-orange-600' },
              { label: 'Novos (30d)', value: statsData.new_last_30d, icon: Sparkles, color: 'from-cyan-500 to-blue-600' },
            ].map(kpi => (
              <div key={kpi.label} className="bg-bg-surface border border-border rounded-2xl p-5">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs text-secondary font-medium">{kpi.label}</span>
                  <div className={`w-8 h-8 rounded-xl bg-gradient-to-br ${kpi.color} flex items-center justify-center`}>
                    <kpi.icon className="w-4 h-4 text-white" />
                  </div>
                </div>
                <div className="text-2xl font-bold text-primary">{kpi.value}</div>
              </div>
            ))}
          </div>

          {/* Funnel breakdown */}
          <div className="bg-bg-surface border border-border rounded-2xl p-6">
            <h3 className="font-bold text-lg text-primary mb-4 flex items-center gap-2">
              <Filter className="w-5 h-5 text-indigo-500" /> Funil de Vendas
            </h3>
            <div className="space-y-3">
              {stages.map(stage => {
                const count = statsData.counts[stage.key] || 0;
                const pct = statsData.total > 0 ? (count / statsData.total * 100) : 0;
                const avgScore = statsData.avg_score_by_stage[stage.key] || 0;

                return (
                  <div key={stage.key} className="flex items-center gap-4">
                    <span className="text-lg w-8">{stage.emoji}</span>
                    <span className="text-xs font-bold text-primary w-40">{stage.label}</span>
                    <div className="flex-1 h-8 bg-bg-sidebar rounded-lg overflow-hidden relative">
                      <div
                        className="h-full rounded-lg transition-all duration-500 flex items-center px-3"
                        style={{
                          width: `${Math.max(pct, 2)}%`,
                          backgroundColor: stage.color,
                          opacity: 0.7,
                        }}
                      >
                        <span className="text-[10px] font-bold text-white whitespace-nowrap">
                          {count} ({pct.toFixed(0)}%)
                        </span>
                      </div>
                    </div>
                    <span className="text-[10px] text-secondary w-16 text-right">
                      Score: {avgScore}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* TAB: INTELLIGENCE (AC Dashboard) */}
      {tab === 'intelligence' && (
        <div className="space-y-6">
          {/* Action buttons */}
          <div className="flex gap-3">
            <button
              onClick={() => engRecalc.mutate()}
              disabled={engRecalc.isPending}
              className="flex items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-cyan-500 to-blue-600 text-white rounded-xl text-xs font-bold shadow-lg hover:scale-105 transition-all"
            >
              {engRecalc.isPending ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Activity className="w-4 h-4" />}
              Recalcular Engagement
            </button>
            <button
              onClick={() => winRecalc.mutate()}
              disabled={winRecalc.isPending}
              className="flex items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-emerald-500 to-green-600 text-white rounded-xl text-xs font-bold shadow-lg hover:scale-105 transition-all"
            >
              {winRecalc.isPending ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Target className="w-4 h-4" />}
              Recalcular Win Probability
            </button>
          </div>

          {/* AC KPIs */}
          {acDash && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[
                { label: 'Tarefas Pendentes', value: acDash.tasks_pending, icon: ListChecks, color: 'from-amber-500 to-orange-600', sub: `${acDash.tasks_overdue} atrasadas` },
                { label: 'Conversões (30d)', value: acDash.conversions_30d, icon: Target, color: 'from-emerald-500 to-green-600', sub: '' },
                { label: 'Receita (30d)', value: `R$${acDash.revenue_30d.toLocaleString()}`, icon: DollarSign, color: 'from-indigo-500 to-purple-600', sub: '' },
                { label: 'Pipeline Total', value: `R$${acDash.pipeline_value.toLocaleString()}`, icon: TrendingUp, color: 'from-cyan-500 to-blue-600', sub: '' },
              ].map(kpi => (
                <div key={kpi.label} className="bg-bg-surface border border-border rounded-2xl p-5">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-xs text-secondary font-medium">{kpi.label}</span>
                    <div className={`w-8 h-8 rounded-xl bg-gradient-to-br ${kpi.color} flex items-center justify-center`}>
                      <kpi.icon className="w-4 h-4 text-white" />
                    </div>
                  </div>
                  <div className="text-2xl font-bold text-primary">{kpi.value}</div>
                  {kpi.sub && <div className="text-[10px] text-rose-400 mt-1">{kpi.sub}</div>}
                </div>
              ))}
            </div>
          )}

          {/* Engagement Distribution */}
          {acDash && (
            <div className="bg-bg-surface border border-border rounded-2xl p-6">
              <h3 className="font-bold text-lg text-primary mb-4 flex items-center gap-2">
                <Activity className="w-5 h-5 text-indigo-500" /> Distribuição de Engagement
              </h3>
              <div className="grid grid-cols-4 gap-4">
                {[
                  { key: 'superfan', label: '🔥 Superfan', color: 'from-rose-500 to-pink-600' },
                  { key: 'engaged', label: '✅ Engajado', color: 'from-emerald-500 to-green-600' },
                  { key: 'idle', label: '💤 Idle', color: 'from-amber-500 to-orange-600' },
                  { key: 'inactive', label: '❌ Inativo', color: 'from-gray-500 to-gray-600' },
                ].map(eng => (
                  <div key={eng.key} className="text-center p-4 bg-bg-sidebar rounded-xl">
                    <div className="text-2xl font-bold text-primary">{acDash.engagement[eng.key] || 0}</div>
                    <div className="text-xs text-secondary mt-1">{eng.label}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Revenue Forecast */}
          {forecastData && (
            <div className="bg-bg-surface border border-border rounded-2xl p-6">
              <h3 className="font-bold text-lg text-primary mb-4 flex items-center gap-2">
                <DollarSign className="w-5 h-5 text-emerald-500" /> Revenue Forecast
              </h3>
              <div className="grid grid-cols-3 gap-4 mb-6">
                <div className="text-center p-4 bg-bg-sidebar rounded-xl">
                  <div className="text-xs text-secondary mb-1">Pipeline Total</div>
                  <div className="text-xl font-bold text-primary">R${forecastData.total_pipeline_value.toLocaleString()}</div>
                </div>
                <div className="text-center p-4 bg-bg-sidebar rounded-xl">
                  <div className="text-xs text-secondary mb-1">Forecast Ponderado</div>
                  <div className="text-xl font-bold text-emerald-400">R${forecastData.weighted_forecast.toLocaleString()}</div>
                </div>
                <div className="text-center p-4 bg-bg-sidebar rounded-xl">
                  <div className="text-xs text-secondary mb-1">Leads Ativos</div>
                  <div className="text-xl font-bold text-primary">{forecastData.total_leads}</div>
                </div>
              </div>
              <div className="space-y-2">
                {stages.filter(s => s.key !== 'perdido').map(stage => {
                  const data = forecastData.by_stage[stage.key];
                  if (!data) return null;
                  return (
                    <div key={stage.key} className="flex items-center gap-3 text-xs">
                      <span className="w-6 text-center">{stage.emoji}</span>
                      <span className="w-40 font-bold text-primary">{stage.label}</span>
                      <span className="text-secondary">{data.count} leads</span>
                      <span className="text-primary font-bold">R${data.raw_value.toLocaleString()}</span>
                      <span className="text-emerald-400">→ R${data.weighted_value.toLocaleString()} ponderado</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Conversion Attribution */}
          {convData && convData.by_source.length > 0 && (
            <div className="bg-bg-surface border border-border rounded-2xl p-6">
              <h3 className="font-bold text-lg text-primary mb-4 flex items-center gap-2">
                <Percent className="w-5 h-5 text-amber-500" /> Conversion Attribution (30d)
              </h3>
              <div className="space-y-3">
                {convData.by_source.map((src, i) => (
                  <div key={i} className="flex items-center gap-4">
                    <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center flex-shrink-0">
                      <span className="text-white text-xs font-bold">#{i+1}</span>
                    </div>
                    <div className="flex-1">
                      <div className="text-sm font-bold text-primary">{src.source}</div>
                      <div className="text-[10px] text-secondary">{src.type} • {src.count} conversões</div>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-bold text-emerald-400">R${src.value.toLocaleString()}</div>
                    </div>
                  </div>
                ))}
              </div>
              <div className="mt-4 pt-4 border-t border-border flex justify-between">
                <span className="text-xs text-secondary font-bold">Total</span>
                <span className="text-sm font-bold text-primary">R${convData.total_value.toLocaleString()} ({convData.total_conversions} conversões)</span>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
