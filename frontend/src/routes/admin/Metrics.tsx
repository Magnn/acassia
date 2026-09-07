import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  TrendingUp, TrendingDown, Users, DollarSign, AlertTriangle,
  CreditCard, Activity, Target, ArrowRight,
} from 'lucide-react';
import { adminApi } from '../../api/admin';

const PLAN_COLORS: Record<string, string> = {
  free: 'bg-zinc-700',
  starter: 'bg-blue-600',
  pro: 'bg-purple-600',
  enterprise: 'bg-amber-600',
};

function fmtBRL(value: number): string {
  return value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

export default function AdminMetrics() {
  const [topBy, setTopBy] = useState<'mrr' | 'msgs_30d' | 'leads_30d'>('mrr');

  const { data: summary, isLoading: loadingSummary } = useQuery({
    queryKey: ['admin-metrics-summary'],
    queryFn: adminApi.metricsSummary,
    staleTime: 60_000,
  });
  const { data: mrrHistory } = useQuery({
    queryKey: ['admin-metrics-mrr-history'],
    queryFn: () => adminApi.metricsMRRHistory(12),
    staleTime: 5 * 60_000,
  });
  const { data: cohort } = useQuery({
    queryKey: ['admin-metrics-cohort'],
    queryFn: () => adminApi.metricsCohort(12),
    staleTime: 5 * 60_000,
  });
  const { data: funnel } = useQuery({
    queryKey: ['admin-metrics-funnel'],
    queryFn: adminApi.metricsFunnel,
    staleTime: 5 * 60_000,
  });
  const { data: topTenants } = useQuery({
    queryKey: ['admin-metrics-top', topBy],
    queryFn: () => adminApi.metricsTopTenants(topBy, 10),
    staleTime: 60_000,
  });

  if (loadingSummary || !summary) {
    return (
      <div className="p-8 space-y-4 animate-pulse">
        <div className="h-8 w-1/3 bg-zinc-900 rounded" />
        <div className="grid grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-32 bg-zinc-900 rounded-2xl" />
          ))}
        </div>
      </div>
    );
  }

  const maxMRR = Math.max(...(mrrHistory?.history.map((m) => m.mrr_brl) ?? [0]));

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      <div>
        <h1 className="text-2xl font-black tracking-tight">Métricas de Negócio</h1>
        <p className="text-zinc-500 text-sm font-medium mt-1">
          Atualizado {new Date(summary.computed_at).toLocaleTimeString('pt-BR')}
        </p>
      </div>

      {/* Cards top */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <BigCard
          icon={DollarSign}
          label="MRR"
          value={fmtBRL(summary.mrr_brl)}
          subtitle={`${summary.paying_tenants} pagantes`}
          color="text-emerald-400"
        />
        <BigCard
          icon={Users}
          label="Tenants ativos"
          value={summary.active_tenants.toLocaleString('pt-BR')}
          subtitle={`+${summary.new_signups_30d} novos 30d`}
          color="text-blue-400"
        />
        <BigCard
          icon={TrendingDown}
          label="Churn 30d"
          value={`${summary.churn_rate_30d_pct}%`}
          subtitle={`${summary.churned_30d} cancelados`}
          color="text-red-400"
        />
        <BigCard
          icon={CreditCard}
          label="ARPU"
          value={fmtBRL(summary.arpu_brl)}
          subtitle="Receita / pagante"
          color="text-amber-400"
        />
        <BigCard
          icon={TrendingUp}
          label="LTV"
          value={summary.ltv_unbounded ? '∞' : fmtBRL(summary.ltv_brl ?? 0)}
          subtitle={summary.ltv_unbounded ? 'churn=0 (low data)' : 'estimado'}
          color="text-purple-400"
        />
        <BigCard
          icon={AlertTriangle}
          label="Trial 7d"
          value={summary.trial_expiring_7d.toLocaleString('pt-BR')}
          subtitle={`${summary.dunning_count} dunning`}
          color="text-amber-400"
        />
      </div>

      {/* MRR history + plans distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-zinc-900/50 border border-zinc-800 rounded-2xl p-6">
          <h3 className="text-xs font-black uppercase tracking-widest text-zinc-400 mb-4">
            MRR — últimos 12 meses
          </h3>
          {mrrHistory && mrrHistory.history.length > 0 ? (
            <div className="space-y-2">
              {mrrHistory.history.map((m) => (
                <div key={m.month} className="flex items-center gap-3 text-xs">
                  <span className="text-zinc-500 w-14 font-mono">{m.month}</span>
                  <div className="flex-1 h-6 bg-zinc-950 rounded relative overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-emerald-600 to-emerald-400 transition-all"
                      style={{ width: maxMRR > 0 ? `${(m.mrr_brl / maxMRR) * 100}%` : '0%' }}
                    />
                  </div>
                  <span className="text-white font-mono w-24 text-right">{fmtBRL(m.mrr_brl)}</span>
                  <span className="text-zinc-500 font-mono w-12 text-right">{m.paying_tenants}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-zinc-600 text-sm text-center py-8">Sem dados</div>
          )}
        </div>

        <div className="bg-zinc-900/50 border border-zinc-800 rounded-2xl p-6">
          <h3 className="text-xs font-black uppercase tracking-widest text-zinc-400 mb-4">
            Distribuição por plano
          </h3>
          <div className="space-y-3">
            {Object.entries(summary.plans_distribution).map(([plan, count]) => {
              const total = Object.values(summary.plans_distribution).reduce((a, b) => a + b, 0);
              const pct = total > 0 ? (count / total) * 100 : 0;
              return (
                <div key={plan}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-bold capitalize">{plan}</span>
                    <span className="text-xs text-zinc-500 font-mono">
                      {count} ({pct.toFixed(0)}%)
                    </span>
                  </div>
                  <div className="h-2 bg-zinc-950 rounded-full overflow-hidden">
                    <div
                      className={`h-full ${PLAN_COLORS[plan] || 'bg-zinc-700'}`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Funnel */}
      {funnel && (
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-2xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xs font-black uppercase tracking-widest text-zinc-400">
              <Target className="inline w-3.5 h-3.5 mr-2" />
              Funnel de ativação ({funnel.period_days}d)
            </h3>
          </div>
          <div className="space-y-2">
            {funnel.steps.map((s, i) => {
              const widthPct = s.pct_total;
              return (
                <div key={s.key} className="flex items-center gap-4">
                  <div className="w-44 flex-shrink-0">
                    <div className="text-sm font-bold">{s.label}</div>
                    <div className="text-[10px] text-zinc-500 font-mono">{s.count} tenants</div>
                  </div>
                  <div className="flex-1 h-8 bg-zinc-950 rounded-lg overflow-hidden relative">
                    <div
                      className="h-full bg-gradient-to-r from-purple-600 to-blue-600"
                      style={{ width: `${widthPct}%` }}
                    />
                    <span className="absolute inset-0 flex items-center px-3 text-xs font-mono font-bold">
                      {widthPct.toFixed(1)}%
                    </span>
                  </div>
                  {i > 0 && s.drop_pct !== undefined && (
                    <div className={`w-20 text-right text-xs font-mono ${
                      s.drop_pct > 50 ? 'text-red-500' : s.drop_pct > 25 ? 'text-amber-500' : 'text-zinc-500'
                    }`}>
                      ▼ {s.drop_pct.toFixed(0)}%
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Cohort retention */}
      {cohort && cohort.cohorts.length > 0 && (
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-2xl p-6 overflow-x-auto">
          <h3 className="text-xs font-black uppercase tracking-widest text-zinc-400 mb-4">
            Cohort retention
          </h3>
          <table className="w-full text-xs font-mono">
            <thead>
              <tr className="text-left text-[10px] uppercase tracking-widest text-zinc-500">
                <th className="px-2 py-2 sticky left-0 bg-zinc-900/50">Cohort</th>
                <th className="px-2 py-2">Size</th>
                {Array.from({ length: cohort.months_tracked }).map((_, i) => (
                  <th key={i} className="px-2 py-2 text-center">M+{i}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {cohort.cohorts.map((c) => (
                <tr key={c.cohort} className="border-t border-zinc-900">
                  <td className="px-2 py-1.5 font-bold sticky left-0 bg-zinc-900/50">
                    {c.cohort}
                    {c.low_confidence && <span className="ml-1 text-amber-500" title="Sample < 10">⚠</span>}
                  </td>
                  <td className="px-2 py-1.5 text-zinc-500">{c.size}</td>
                  {c.retention.map((r, i) => {
                    if (r === null) return <td key={i} className="px-2 py-1.5 text-zinc-700">—</td>;
                    const intensity = r.pct;
                    const bg = intensity > 80 ? 'bg-emerald-900/60' :
                               intensity > 60 ? 'bg-emerald-800/40' :
                               intensity > 40 ? 'bg-amber-800/30' :
                               intensity > 20 ? 'bg-red-800/30' : 'bg-red-900/50';
                    return (
                      <td key={i} className={`px-2 py-1.5 text-center ${bg}`}>
                        {r.pct.toFixed(0)}%
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Top tenants */}
      <div className="bg-zinc-900/50 border border-zinc-800 rounded-2xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xs font-black uppercase tracking-widest text-zinc-400">
            <Activity className="inline w-3.5 h-3.5 mr-2" />
            Top tenants
          </h3>
          <div className="flex gap-1 bg-zinc-950 p-1 rounded-lg">
            {(['mrr', 'msgs_30d', 'leads_30d'] as const).map((k) => (
              <button
                key={k}
                onClick={() => setTopBy(k)}
                className={`px-3 py-1 rounded text-[10px] font-black uppercase tracking-widest transition-all ${
                  topBy === k ? 'bg-zinc-800 text-white' : 'text-zinc-500 hover:text-white'
                }`}
              >
                {k === 'mrr' ? 'MRR' : k === 'msgs_30d' ? 'Msgs 30d' : 'Leads 30d'}
              </button>
            ))}
          </div>
        </div>
        {topTenants && topTenants.tenants.length > 0 ? (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-[10px] font-black uppercase tracking-widest text-zinc-500 border-b border-zinc-800">
                <th className="px-3 py-2">#</th>
                <th className="px-3 py-2">Tenant</th>
                <th className="px-3 py-2 text-right">MRR</th>
                <th className="px-3 py-2 text-right">Leads 30d</th>
                <th className="px-3 py-2 text-right">Msgs 30d</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {topTenants.tenants.map((t, i) => (
                <tr key={t.tenant_id} className="border-b border-zinc-900/50 hover:bg-zinc-900/30">
                  <td className="px-3 py-2 text-zinc-600 font-mono">{i + 1}</td>
                  <td className="px-3 py-2">
                    <div className="font-bold truncate max-w-[200px]">{t.email}</div>
                    <div className="text-[10px] text-zinc-600 font-mono truncate max-w-[200px]">{t.tenant_id}</div>
                  </td>
                  <td className="px-3 py-2 text-right font-mono">{fmtBRL(t.mrr_brl)}</td>
                  <td className="px-3 py-2 text-right text-zinc-300 font-mono">{t.leads_30d}</td>
                  <td className="px-3 py-2 text-right text-zinc-300 font-mono">{t.msgs_30d}</td>
                  <td className="px-3 py-2">
                    <Link
                      to={`/admin/tenants/${t.tenant_id}`}
                      className="text-zinc-500 hover:text-white"
                    >
                      <ArrowRight className="w-3.5 h-3.5" />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="text-zinc-600 text-sm text-center py-8">Sem dados ainda</div>
        )}
      </div>
    </div>
  );
}

function BigCard({
  icon: Icon, label, value, subtitle, color,
}: {
  icon: typeof TrendingUp;
  label: string;
  value: string;
  subtitle: string;
  color: string;
}) {
  return (
    <div className="bg-zinc-900/50 border border-zinc-800 rounded-2xl p-4">
      <div className="flex items-center gap-2 mb-2">
        <Icon className={`w-3.5 h-3.5 ${color}`} />
        <span className="text-[9px] font-black uppercase tracking-widest text-zinc-500">{label}</span>
      </div>
      <div className="text-2xl font-black tracking-tight">{value}</div>
      <div className="text-[10px] text-zinc-500 mt-1 truncate">{subtitle}</div>
    </div>
  );
}
