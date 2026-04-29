import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  TrendingDown, AlertTriangle, Target, Clock, ArrowRight, BarChart3,
} from 'lucide-react';
import { analyticsApi } from '../api/analytics';

const PERIOD_OPTIONS = [7, 14, 30, 90];

export default function Funnel() {
  const navigate = useNavigate();
  const [periodDays, setPeriodDays] = useState(30);
  const [selectedFlow, setSelectedFlow] = useState<{ id: number | null; slug: string | null } | null>(null);
  const [scoreBand, setScoreBand] = useState<'all' | 'hot' | 'warm' | 'cold'>('all');

  const { data: flowsData, isLoading: flowsLoading } = useQuery({
    queryKey: ['analytics-flows', periodDays],
    queryFn: () => analyticsApi.flows(periodDays),
  });

  const { data: funnel, isLoading: funnelLoading } = useQuery({
    queryKey: ['analytics-funnel', selectedFlow, periodDays, scoreBand],
    queryFn: () => analyticsApi.funnel({
      flow_id: selectedFlow?.id || undefined,
      flow_slug: selectedFlow?.slug || undefined,
      period_days: periodDays,
      score_band: scoreBand === 'all' ? undefined : scoreBand,
    }),
    enabled: !!selectedFlow,
  });

  const flows = flowsData?.flows ?? [];
  const maxEntered = Math.max(...(funnel?.steps?.map(s => s.entered) ?? [1]));

  return (
    <div className="p-10 max-w-6xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-black tracking-tight">Funnel Waterfall</h1>
          <p className="text-secondary text-sm font-medium mt-1">
            Onde os leads escapam — e o que dá pra reescrever
          </p>
        </div>
        <button
          onClick={() => navigate('/dashboard')}
          className="text-xs text-secondary hover:text-primary"
        >
          ← Voltar
        </button>
      </div>

      {/* Filters */}
      <div className="bg-bg-surface border border-border rounded-2xl p-4 flex items-center gap-3 flex-wrap">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-black uppercase tracking-widest text-secondary">Período:</span>
          {PERIOD_OPTIONS.map((d) => (
            <button
              key={d}
              onClick={() => setPeriodDays(d)}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                periodDays === d
                  ? 'bg-accent-amethyst text-white'
                  : 'bg-bg-primary text-secondary hover:text-primary'
              }`}
            >
              {d}d
            </button>
          ))}
        </div>
        <div className="h-6 w-px bg-border" />
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-black uppercase tracking-widest text-secondary">Segmento:</span>
          {(['all', 'hot', 'warm', 'cold'] as const).map((b) => (
            <button
              key={b}
              onClick={() => setScoreBand(b)}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all capitalize ${
                scoreBand === b
                  ? 'bg-accent-amethyst text-white'
                  : 'bg-bg-primary text-secondary hover:text-primary'
              }`}
            >
              {b === 'all' ? 'Todos' : b}
            </button>
          ))}
        </div>
      </div>

      {/* Flow picker */}
      {!selectedFlow && (
        <div className="space-y-4">
          <h3 className="text-sm font-black uppercase tracking-widest text-secondary">
            Escolha um fluxo pra analisar
          </h3>
          {flowsLoading ? (
            <div className="text-secondary text-sm">Carregando...</div>
          ) : flows.length === 0 ? (
            <div className="bg-bg-surface border border-dashed border-border rounded-3xl p-12 text-center">
              <BarChart3 className="w-12 h-12 mx-auto text-secondary/40 mb-4" />
              <p className="text-secondary">
                Nenhum fluxo teve atividade nos últimos {periodDays} dias.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {flows.map((f) => (
                <button
                  key={`${f.flow_id}-${f.flow_slug}`}
                  onClick={() => setSelectedFlow({ id: f.flow_id, slug: f.flow_slug })}
                  className="p-5 bg-bg-surface border border-border hover:border-accent-amethyst/30 rounded-2xl text-left transition-all group"
                >
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-black text-sm tracking-tight">
                      {f.flow_slug || `Flow #${f.flow_id}`}
                    </h4>
                    <ArrowRight className="w-4 h-4 text-secondary group-hover:text-accent-amethyst" />
                  </div>
                  <div className="flex items-center gap-3 text-[11px] text-secondary">
                    <span>{f.unique_leads} leads únicos</span>
                    <span>·</span>
                    <span>{f.visits} visitas</span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Funnel waterfall */}
      {selectedFlow && (
        <>
          <div className="flex items-center justify-between">
            <button
              onClick={() => setSelectedFlow(null)}
              className="text-xs text-secondary hover:text-primary"
            >
              ← Trocar fluxo
            </button>
            {funnel && (
              <div className="flex items-center gap-3 text-xs">
                <span className="text-secondary">
                  {funnel.unique_leads} leads · {funnel.total_runs} visitas
                </span>
                {funnel.low_confidence && (
                  <span className="px-2 py-1 bg-amber-500/10 border border-amber-500/30 rounded text-amber-400 font-bold">
                    Amostra baixa
                  </span>
                )}
              </div>
            )}
          </div>

          {funnelLoading ? (
            <div className="text-secondary text-sm">Carregando funnel...</div>
          ) : !funnel || funnel.steps.length === 0 ? (
            <div className="text-secondary text-sm text-center py-12">
              Sem dados pra esse fluxo no período.
            </div>
          ) : (
            <>
              {/* Conversion overall */}
              <div className="bg-gradient-to-br from-accent-amethyst/10 to-transparent border border-accent-amethyst/20 rounded-3xl p-8 text-center">
                <Target className="w-10 h-10 mx-auto text-accent-amethyst mb-3" />
                <div className="text-5xl font-black tracking-tight">
                  {funnel.overall_conversion_pct}%
                </div>
                <div className="text-xs text-secondary mt-2 uppercase tracking-widest">
                  Conversão geral nos últimos {funnel.period_days} dias
                </div>
              </div>

              {/* Waterfall */}
              <div className="space-y-3">
                {funnel.steps.map((step, i) => {
                  const widthPct = (step.entered / maxEntered) * 100;
                  const dropColor =
                    step.drop_pct >= 50 ? 'text-red-500 bg-red-500/10 border-red-500/30' :
                    step.drop_pct >= 30 ? 'text-amber-500 bg-amber-500/10 border-amber-500/30' :
                    'text-emerald-500 bg-emerald-500/10 border-emerald-500/30';

                  return (
                    <div
                      key={step.node_id}
                      className={`p-4 rounded-2xl border ${
                        step.is_high_drop
                          ? 'bg-red-500/5 border-red-500/30'
                          : 'bg-bg-surface border-border'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold text-secondary tabular-nums">
                            {String(i + 1).padStart(2, '0')}.
                          </span>
                          <span className="font-black font-mono text-sm">{step.node_id}</span>
                          {step.is_high_drop && (
                            <AlertTriangle className="w-4 h-4 text-red-500" />
                          )}
                        </div>
                        <div className="flex items-center gap-3 text-[11px]">
                          {step.median_time_s !== null && (
                            <span className="flex items-center gap-1 text-secondary">
                              <Clock className="w-3 h-3" />
                              {fmtDuration(step.median_time_s)}
                            </span>
                          )}
                          <span className="font-mono font-bold">{step.entered.toLocaleString('pt-BR')} entered</span>
                          <span className={`px-2 py-0.5 rounded-md border text-[10px] font-black uppercase tracking-widest ${dropColor}`}>
                            <TrendingDown className="inline w-3 h-3 mr-1" />
                            {step.drop_pct}% drop
                          </span>
                        </div>
                      </div>
                      <div className="h-3 bg-bg-primary rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-accent-amethyst to-purple-400 transition-all"
                          style={{ width: `${widthPct}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Insights */}
              <div className="bg-amber-500/5 border border-amber-500/20 rounded-3xl p-6">
                <h3 className="text-sm font-black mb-3 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-amber-500" />
                  Pontos de atenção
                </h3>
                {funnel.steps.filter(s => s.is_high_drop).length === 0 ? (
                  <p className="text-xs text-secondary">
                    Funnel saudável — nenhum nó com drop acima de 30%.
                  </p>
                ) : (
                  <ul className="space-y-2 text-xs">
                    {funnel.steps.filter(s => s.is_high_drop).map(s => (
                      <li key={s.node_id} className="text-amber-300">
                        <strong className="font-mono">{s.node_id}</strong>: {s.drop_pct}% drop
                        {' '} ({s.drop} de {s.entered} leads escaparam)
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}

function fmtDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}min`;
  return `${Math.round(seconds / 3600)}h`;
}
