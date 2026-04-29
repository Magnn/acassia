import { useQuery } from '@tanstack/react-query';
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { Activity, CheckCircle, DollarSign, PauseCircle, Users } from 'lucide-react';
import { metricsApi } from '../api/metrics';

export default function Dashboard() {
  const { data: kpis, isLoading, error } = useQuery({
    queryKey: ['saas-metrics'],
    queryFn: metricsApi.get,
    refetchInterval: 30000,
  });

  const { data: exec } = useQuery({
    queryKey: ['executive-kpis', 7],
    queryFn: () => metricsApi.getExecutive(7),
    refetchInterval: 60000,
  });

  if (isLoading) {
    return (
      <div className="p-8 max-w-7xl mx-auto flex items-center justify-center h-full">
        <div className="text-slate-400 animate-pulse">Carregando métricas...</div>
      </div>
    );
  }

  if (error || !kpis) {
    return (
      <div className="p-8 max-w-7xl mx-auto">
        <div className="bg-red-500/10 border border-red-500/30 text-red-400 p-4 rounded-xl">
          Falha ao carregar as métricas. {(error as Error)?.message}
        </div>
      </div>
    );
  }

  const series = (exec?.series ?? []).map((p) => ({
    ...p,
    label: p.date.slice(5), // MM-DD
  }));

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <h2 className="text-2xl font-bold mb-6 font-display tracking-tight text-white">
        Dashboard
      </h2>

      {/* KPI cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <KpiCard
          label="Total Leads"
          value={kpis.total_leads}
          hint="Histórico completo"
          Icon={Users}
        />
        <KpiCard
          label="Leads (7d)"
          value={kpis.leads_7d}
          hint={`${kpis.leads_30d} nos últimos 30d`}
          Icon={Activity}
          accent="text-sky-400"
        />
        <KpiCard
          label="Convertidos"
          value={kpis.convertidos}
          hint={`${kpis.conversion_rate}% taxa`}
          Icon={CheckCircle}
          accent="text-emerald-400"
          valueAccent="text-emerald-400"
        />
        <KpiCard
          label="Ativas"
          value={kpis.ativas}
          hint={`${kpis.pausadas} pausadas · ${kpis.opt_out} opt-out`}
          Icon={PauseCircle}
          accent="text-amber-400"
        />
      </div>

      {/* Faturamento — só se backend retornou série */}
      {exec && series.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
          <div className="bg-cigana-surface border border-cigana-border rounded-xl p-5 shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <DollarSign className="w-4 h-4 text-emerald-400" />
                <h3 className="font-bold text-slate-200 text-sm">
                  Faturamento (7d)
                </h3>
              </div>
              <span className="text-xs text-slate-500">
                hoje:{' '}
                <strong className="text-emerald-400">
                  {brl(exec.revenue_today ?? 0)}
                </strong>
              </span>
            </div>
            <ResponsiveContainer width="100%" height={180}>
              <AreaChart data={series}>
                <defs>
                  <linearGradient id="revGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#10b981" stopOpacity={0.4} />
                    <stop offset="100%" stopColor="#10b981" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="#334155" strokeDasharray="3 3" />
                <XAxis dataKey="label" stroke="#94a3b8" fontSize={11} />
                <YAxis stroke="#94a3b8" fontSize={11} tickFormatter={(v) => `R$${v}`} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1e293b',
                    border: '1px solid #334155',
                    borderRadius: 8,
                    fontSize: 12,
                  }}
                  formatter={(v: number) => brl(v)}
                />
                <Area
                  type="monotone"
                  dataKey="revenue_brl"
                  stroke="#10b981"
                  fill="url(#revGrad)"
                  strokeWidth={2}
                  name="Receita"
                />
                <Area
                  type="monotone"
                  dataKey="profit_brl"
                  stroke="#7c3aed"
                  fill="none"
                  strokeWidth={2}
                  strokeDasharray="4 2"
                  name="Lucro"
                />
                <Legend wrapperStyle={{ fontSize: 11 }} />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          <div className="bg-cigana-surface border border-cigana-border rounded-xl p-5 shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Activity className="w-4 h-4 text-sky-400" />
                <h3 className="font-bold text-slate-200 text-sm">
                  Vendas por dia
                </h3>
              </div>
              <span className="text-xs text-slate-500">
                hoje:{' '}
                <strong className="text-sky-400">
                  {exec.sales_count_today ?? 0}
                </strong>
              </span>
            </div>
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={series}>
                <CartesianGrid stroke="#334155" strokeDasharray="3 3" />
                <XAxis dataKey="label" stroke="#94a3b8" fontSize={11} />
                <YAxis stroke="#94a3b8" fontSize={11} allowDecimals={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1e293b',
                    border: '1px solid #334155',
                    borderRadius: 8,
                    fontSize: 12,
                  }}
                />
                <Bar
                  dataKey="transactions_count"
                  fill="#7c3aed"
                  radius={[4, 4, 0, 0]}
                  name="Vendas"
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Distribuição no funil */}
      <div className="bg-cigana-surface border border-cigana-border rounded-xl p-6 shadow-sm">
        <h3 className="font-bold mb-4 text-slate-200">
          Distribuição no Funil (Top 5)
        </h3>
        {kpis.node_distribution && kpis.node_distribution.length > 0 ? (
          <div className="space-y-4">
            {kpis.node_distribution.map((nd, idx) => {
              const maxCount = kpis.node_distribution[0].count;
              const width =
                maxCount > 0 ? Math.round((nd.count / maxCount) * 100) : 0;
              return (
                <div key={idx}>
                  <div className="flex justify-between text-[11px] text-slate-400 mb-1.5">
                    <span className="font-mono text-slate-300">{nd.node}</span>
                    <span className="font-bold text-slate-300">{nd.count}</span>
                  </div>
                  <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-cigana-purple rounded-full transition-all duration-1000 ease-out"
                      style={{ width: `${width}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <p className="text-sm text-slate-500 italic">
            Sem dados no funil ainda.
          </p>
        )}
      </div>
    </div>
  );
}

function KpiCard({
  label,
  value,
  hint,
  Icon,
  accent = 'text-slate-500',
  valueAccent = 'text-slate-100',
}: {
  label: string;
  value: number;
  hint: string;
  Icon: typeof Users;
  accent?: string;
  valueAccent?: string;
}) {
  return (
    <div className="bg-cigana-surface border border-cigana-border rounded-xl p-5 shadow-sm hover:border-cigana-purple/40 transition-colors">
      <div className="flex items-center justify-between mb-3">
        <div className="text-xs text-slate-400 uppercase tracking-widest font-semibold">
          {label}
        </div>
        <Icon className={`w-4 h-4 ${accent}`} />
      </div>
      <div className={`text-3xl font-bold ${valueAccent} mb-1`}>{value}</div>
      <div className="text-[11px] text-slate-500">{hint}</div>
    </div>
  );
}

function brl(v: number): string {
  return v.toLocaleString('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  });
}
