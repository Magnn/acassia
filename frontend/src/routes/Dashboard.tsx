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
import LaunchChecklist from '../components/LaunchChecklist';

// Cores dos charts — padrão SaaS B2B.
const CHART = {
  amethyst: '#6366f1',
  ember: '#10b981',
  rose: '#f43f5e',
  grid: '#27272a',
  axis: '#71717a',
};

export default function Dashboard() {
  const { data: kpis, isLoading, error } = useQuery({
    queryKey: ['saas-metrics'],
    queryFn: metricsApi.get,
    staleTime: 5 * 60_000,    // matches Redis cache TTL (300s)
    refetchInterval: 5 * 60_000,
  });

  const { data: exec } = useQuery({
    queryKey: ['executive-kpis', 7],
    queryFn: () => metricsApi.getExecutive(7),
    staleTime: 5 * 60_000,    // matches Redis cache TTL (300s)
    refetchInterval: 5 * 60_000,
  });

  if (isLoading) {
    return (
      <div className="p-12 max-w-7xl mx-auto flex flex-col items-center justify-center min-h-[400px]">
        <div className="w-12 h-12 border-4 border-indigo-500/20 border-t-indigo-500 rounded-full animate-spin mb-4" />
        <div className="text-zinc-400 text-xs font-bold uppercase tracking-widest animate-pulse">
          Consolidando métricas e conversões…
        </div>
      </div>
    );
  }

  if (error || !kpis) {
    return (
      <div className="p-12 max-w-7xl mx-auto">
        <LaunchChecklist />
        <div className="bg-red-500/5 border border-red-500/20 text-red-500 rounded-3xl p-8 text-center shadow-sm">
          <div className="font-black text-xl mb-2">Ops! Falha nas métricas</div>
          <div className="text-sm opacity-80">{(error as Error)?.message}</div>
        </div>
      </div>
    );
  }

  const series = (exec?.series ?? []).map((p) => ({
    ...p,
    label: p.date.slice(5),
  }));

  return (
    <div className="px-8 py-10 max-w-6xl mx-auto space-y-10">
      <div>
        <h2 className="text-4xl font-black tracking-tight text-primary mb-2">
          Visão Geral
        </h2>
        <p className="text-sm text-secondary font-medium max-w-2xl">
          Acompanhe o pulso da sua operação em tempo real. Movimentação de leads, conversões e saúde financeira.
        </p>
      </div>

      {/* KPI cards */}
      <LaunchChecklist />
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          label="Total Leads"
          value={kpis.total_leads}
          hint="Histórico acumulado"
          Icon={Users}
        />
        <KpiCard
          label="Últimos 7 dias"
          value={kpis.leads_7d}
          hint={`${kpis.leads_30d} no mês`}
          Icon={Activity}
          accent="text-accent-amethyst"
          bgAccent="bg-accent-amethyst/5"
        />
        <KpiCard
          label="Convertidos"
          value={kpis.convertidos}
          hint={`${kpis.conversion_rate}% de taxa`}
          Icon={CheckCircle}
          accent="text-emerald-500"
          valueAccent="text-emerald-500"
          bgAccent="bg-emerald-500/5"
        />
        <KpiCard
          label="Sessões Ativas"
          value={kpis.ativas}
          hint={`${kpis.pausadas} em pausa · ${kpis.opt_out} saídas`}
          Icon={PauseCircle}
          accent="text-accent-ember"
          bgAccent="bg-accent-ember/5"
        />
      </div>

      {/* Charts */}
      {exec && series.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Panel
            title="Performance Financeira"
            subtitle="Receita vs Lucro (7d)"
            Icon={DollarSign}
            iconAccent="text-accent-ember"
            metric={`Hoje: ${brl(exec.revenue_today ?? 0)}`}
          >
            <div className="h-[250px] mt-6">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={series} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="revGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={CHART.ember} stopOpacity={0.2} />
                      <stop offset="100%" stopColor={CHART.ember} stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="profGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={CHART.amethyst} stopOpacity={0.15} />
                      <stop offset="100%" stopColor={CHART.amethyst} stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke={CHART.grid} strokeDasharray="3 3" vertical={false} opacity={0.5} />
                  <XAxis
                    dataKey="label"
                    stroke={CHART.axis}
                    fontSize={10}
                    tickLine={false}
                    axisLine={false}
                    dy={10}
                  />
                  <YAxis
                    stroke={CHART.axis}
                    fontSize={10}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(v) => `R$${v}`}
                  />
                  <Tooltip
                    contentStyle={tooltipStyle}
                    itemStyle={{ fontSize: '11px', fontWeight: 'bold' }}
                    formatter={(v: number) => brl(v)}
                    cursor={{ stroke: 'var(--border-primary)', strokeWidth: 1 }}
                  />
                  <Area
                    type="monotone"
                    dataKey="revenue_brl"
                    stroke={CHART.ember}
                    fill="url(#revGrad)"
                    strokeWidth={3}
                    name="Receita"
                    animationDuration={1500}
                  />
                  <Area
                    type="monotone"
                    dataKey="profit_brl"
                    stroke={CHART.amethyst}
                    fill="url(#profGrad)"
                    strokeWidth={2}
                    strokeDasharray="5 5"
                    name="Lucro"
                    animationDuration={2000}
                  />
                  <Legend
                    wrapperStyle={{ fontSize: 11, fontWeight: 'bold', paddingTop: 20 }}
                    iconType="circle"
                    iconSize={8}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </Panel>

          <Panel
            title="Volume de Conversões"
            subtitle="Vendas confirmadas"
            Icon={Activity}
            iconAccent="text-accent-amethyst"
            metric={`Hoje: ${exec.sales_count_today ?? 0} vendas`}
          >
            <div className="h-[250px] mt-6">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={series} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid stroke={CHART.grid} strokeDasharray="3 3" vertical={false} opacity={0.5} />
                  <XAxis
                    dataKey="label"
                    stroke={CHART.axis}
                    fontSize={10}
                    tickLine={false}
                    axisLine={false}
                    dy={10}
                  />
                  <YAxis
                    stroke={CHART.axis}
                    fontSize={10}
                    tickLine={false}
                    axisLine={false}
                    allowDecimals={false}
                  />
                  <Tooltip
                    contentStyle={tooltipStyle}
                    cursor={{ fill: 'var(--bg-primary)', opacity: 0.4 }}
                  />
                  <Bar
                    dataKey="transactions_count"
                    fill={CHART.amethyst}
                    radius={[6, 6, 0, 0]}
                    name="Vendas"
                    barSize={32}
                    animationDuration={1500}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Panel>
        </div>
      )}

      {/* Funil */}
      <Panel title="Distribuição de Contatos" subtitle="Principais etapas do funil de vendas">
        {kpis.node_distribution && kpis.node_distribution.length > 0 ? (
          <div className="grid gap-4 mt-8">
            {kpis.node_distribution.map((nd, idx) => {
              const maxCount = kpis.node_distribution[0].count;
              const width =
                maxCount > 0 ? Math.round((nd.count / maxCount) * 100) : 0;
              return (
                <div key={idx} className="group">
                  <div className="flex justify-between items-end text-xs mb-2">
                    <span className="font-black text-primary uppercase tracking-widest opacity-70 group-hover:opacity-100 transition-opacity">
                       {nd.node}
                    </span>
                    <span className="font-mono font-black text-accent-amethyst text-sm">
                      {nd.count}
                    </span>
                  </div>
                  <div className="w-full h-3 bg-bg-primary rounded-full overflow-hidden border border-border/50 p-0.5">
                    <div
                      className="h-full bg-gradient-to-r from-accent-amethyst to-accent-ember rounded-full transition-all duration-1000 ease-out shadow-sm"
                      style={{ width: `${width}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="py-12 text-center">
            <p className="text-sm text-secondary italic">
              Nenhum dado de movimentação detectado no funil até o momento.
            </p>
          </div>
        )}
      </Panel>
    </div>
  );
}

const tooltipStyle = {
  backgroundColor: 'var(--bg-surface)',
  border: '1px solid var(--border-border)',
  borderRadius: '12px',
  padding: '12px',
  boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
  color: 'var(--text-primary)',
};

function KpiCard({
  label,
  value,
  hint,
  Icon,
  accent = 'text-secondary',
  valueAccent = 'text-primary',
  bgAccent = 'bg-bg-primary',
}: {
  label: string;
  value: number;
  hint: string;
  Icon: typeof Users;
  accent?: string;
  valueAccent?: string;
  bgAccent?: string;
}) {
  return (
    <div className="bg-bg-surface border border-border rounded-3xl p-6 hover:shadow-xl hover:-translate-y-1 transition-all group overflow-hidden relative">
      <div className={`absolute top-0 right-0 w-24 h-24 ${bgAccent} rounded-bl-full opacity-50 -mr-8 -mt-8 transition-transform group-hover:scale-110`} />
      <div className="relative z-10">
        <div className="flex items-center justify-between mb-4">
          <div className="text-[10px] text-secondary font-black uppercase tracking-[0.15em]">
            {label}
          </div>
          <div className={`p-2 rounded-xl ${bgAccent} ${accent}`}>
            <Icon className="w-4 h-4" strokeWidth={2.5} />
          </div>
        </div>
        <div className={`font-black text-4xl leading-none tracking-tight ${valueAccent} tabular-nums`}>
          {value}
        </div>
        <div className="text-[11px] text-secondary font-bold mt-4 flex items-center gap-2">
           <span className="w-1 h-1 rounded-full bg-border" />
           {hint}
        </div>
      </div>
    </div>
  );
}

function Panel({
  title,
  subtitle,
  Icon,
  iconAccent = 'text-accent-amethyst',
  metric,
  children,
}: {
  title: string;
  subtitle?: string;
  Icon?: typeof Users;
  iconAccent?: string;
  metric?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="bg-bg-surface border border-border rounded-[32px] p-8 shadow-sm hover:shadow-md transition-shadow">
      <header className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          {Icon && (
            <div className={`p-3 rounded-2xl bg-bg-primary ${iconAccent} border border-border/50 shadow-sm`}>
               <Icon className="w-5 h-5" strokeWidth={2.5} />
            </div>
          )}
          <div>
            <h3 className="font-black text-lg text-primary leading-tight tracking-tight">
              {title}
            </h3>
            {subtitle && (
              <span className="text-[10px] text-secondary font-black uppercase tracking-widest opacity-60 mt-1 block">
                {subtitle}
              </span>
            )}
          </div>
        </div>
        {metric && (
          <div className="bg-bg-primary px-4 py-1.5 rounded-full border border-border shadow-inner">
             <span className="text-[11px] font-black text-primary tabular-nums uppercase tracking-tighter">{metric}</span>
          </div>
        )}
      </header>
      {children}
    </section>
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
