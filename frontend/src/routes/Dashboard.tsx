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

const CHART = {
  amethyst: '#7c6a99',
  ember: '#d4a574',
  rose: '#b46e7c',
  grid: '#2a2538',
  axis: '#6b6677',
};

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
      <div className="p-12 max-w-7xl mx-auto">
        <div className="text-sibila-smoke text-sm animate-pulse-soft">
          Consultando os astros…
        </div>
      </div>
    );
  }

  if (error || !kpis) {
    return (
      <div className="p-12 max-w-7xl mx-auto">
        <div className="bg-sibila-crimson/10 border border-sibila-crimson/30 text-sibila-crimson rounded-lg p-4 text-sm">
          Falha ao carregar as métricas. {(error as Error)?.message}
        </div>
      </div>
    );
  }

  const series = (exec?.series ?? []).map((p) => ({
    ...p,
    label: p.date.slice(5),
  }));

  return (
    <div className="px-8 py-10 max-w-6xl mx-auto">
      <div className="mb-8">
        <h2 className="font-display text-3xl text-sibila-moonlight tracking-tight mb-1">
          Visão Geral
        </h2>
        <p className="text-sm text-sibila-smoke">
          Movimento dos últimos dias — leads, conversões e faturamento.
        </p>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mb-8">
        <KpiCard
          label="Total leads"
          value={kpis.total_leads}
          hint="Histórico completo"
          Icon={Users}
        />
        <KpiCard
          label="Últimos 7 dias"
          value={kpis.leads_7d}
          hint={`${kpis.leads_30d} nos últimos 30d`}
          Icon={Activity}
          accent="text-sibila-amethyst"
        />
        <KpiCard
          label="Convertidos"
          value={kpis.convertidos}
          hint={`${kpis.conversion_rate}% de taxa`}
          Icon={CheckCircle}
          accent="text-sibila-sage"
          valueAccent="text-sibila-sage"
        />
        <KpiCard
          label="Ativas agora"
          value={kpis.ativas}
          hint={`${kpis.pausadas} pausadas · ${kpis.opt_out} opt-out`}
          Icon={PauseCircle}
          accent="text-sibila-ember"
        />
      </div>

      {/* Charts */}
      {exec && series.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 mb-8">
          <Panel
            title="Faturamento"
            subtitle="últimos 7 dias"
            Icon={DollarSign}
            iconAccent="text-sibila-ember"
            metric={`hoje · ${brl(exec.revenue_today ?? 0)}`}
          >
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={series} margin={{ top: 5, right: 8, left: -10, bottom: 0 }}>
                <defs>
                  <linearGradient id="revGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={CHART.ember} stopOpacity={0.4} />
                    <stop offset="100%" stopColor={CHART.ember} stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="profGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={CHART.amethyst} stopOpacity={0.25} />
                    <stop offset="100%" stopColor={CHART.amethyst} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke={CHART.grid} strokeDasharray="2 4" vertical={false} />
                <XAxis
                  dataKey="label"
                  stroke={CHART.axis}
                  fontSize={10}
                  tickLine={false}
                  axisLine={false}
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
                  formatter={(v: number) => brl(v)}
                />
                <Area
                  type="monotone"
                  dataKey="revenue_brl"
                  stroke={CHART.ember}
                  fill="url(#revGrad)"
                  strokeWidth={1.8}
                  name="Receita"
                />
                <Area
                  type="monotone"
                  dataKey="profit_brl"
                  stroke={CHART.amethyst}
                  fill="url(#profGrad)"
                  strokeWidth={1.4}
                  strokeDasharray="3 2"
                  name="Lucro"
                />
                <Legend
                  wrapperStyle={{ fontSize: 10, paddingTop: 8 }}
                  iconType="circle"
                  iconSize={6}
                />
              </AreaChart>
            </ResponsiveContainer>
          </Panel>

          <Panel
            title="Vendas por dia"
            subtitle="conversões fechadas"
            Icon={Activity}
            iconAccent="text-sibila-amethyst"
            metric={`hoje · ${exec.sales_count_today ?? 0}`}
          >
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={series} margin={{ top: 5, right: 8, left: -10, bottom: 0 }}>
                <CartesianGrid stroke={CHART.grid} strokeDasharray="2 4" vertical={false} />
                <XAxis
                  dataKey="label"
                  stroke={CHART.axis}
                  fontSize={10}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  stroke={CHART.axis}
                  fontSize={10}
                  tickLine={false}
                  axisLine={false}
                  allowDecimals={false}
                />
                <Tooltip contentStyle={tooltipStyle} cursor={{ fill: '#1c1828' }} />
                <Bar
                  dataKey="transactions_count"
                  fill={CHART.amethyst}
                  radius={[3, 3, 0, 0]}
                  name="Vendas"
                />
              </BarChart>
            </ResponsiveContainer>
          </Panel>
        </div>
      )}

      {/* Funil */}
      <Panel title="Distribuição no Funil" subtitle="Top 5 etapas">
        {kpis.node_distribution && kpis.node_distribution.length > 0 ? (
          <div className="space-y-3.5 mt-2">
            {kpis.node_distribution.map((nd, idx) => {
              const maxCount = kpis.node_distribution[0].count;
              const width =
                maxCount > 0 ? Math.round((nd.count / maxCount) * 100) : 0;
              return (
                <div key={idx}>
                  <div className="flex justify-between text-[11px] mb-1.5">
                    <span className="font-mono text-sibila-fog">{nd.node}</span>
                    <span className="font-medium text-sibila-moonlight tabular-nums">
                      {nd.count}
                    </span>
                  </div>
                  <div className="w-full h-1 bg-sibila-veil rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-sibila-amethyst to-sibila-ember rounded-full transition-all duration-1000 ease-out"
                      style={{ width: `${width}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <p className="text-sm text-sibila-smoke italic mt-2">
            Sem dados no funil ainda.
          </p>
        )}
      </Panel>
    </div>
  );
}

const tooltipStyle = {
  backgroundColor: '#14101e',
  border: '1px solid #2a2538',
  borderRadius: 6,
  fontSize: 11,
  color: '#f3eee5',
};

function KpiCard({
  label,
  value,
  hint,
  Icon,
  accent = 'text-sibila-fog',
  valueAccent = 'text-sibila-moonlight',
}: {
  label: string;
  value: number;
  hint: string;
  Icon: typeof Users;
  accent?: string;
  valueAccent?: string;
}) {
  return (
    <div className="bg-sibila-obsidian border border-sibila-mist rounded-lg px-5 py-4 hover:border-sibila-stone transition-colors shadow-inset-veil">
      <div className="flex items-center justify-between mb-3">
        <div className="text-[10px] text-sibila-smoke uppercase tracking-widest-2 font-semibold">
          {label}
        </div>
        <Icon className={`w-3.5 h-3.5 ${accent}`} strokeWidth={1.8} />
      </div>
      <div className={`font-display text-[28px] leading-none ${valueAccent} tabular-nums`}>
        {value}
      </div>
      <div className="text-[11px] text-sibila-smoke mt-2">{hint}</div>
    </div>
  );
}

function Panel({
  title,
  subtitle,
  Icon,
  iconAccent = 'text-sibila-amethyst',
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
    <section className="bg-sibila-obsidian border border-sibila-mist rounded-lg p-5 shadow-inset-veil">
      <header className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          {Icon && <Icon className={`w-3.5 h-3.5 ${iconAccent}`} strokeWidth={1.8} />}
          <div>
            <h3 className="font-display text-[15px] text-sibila-moonlight leading-none">
              {title}
            </h3>
            {subtitle && (
              <span className="text-[10px] text-sibila-smoke uppercase tracking-wider-2">
                {subtitle}
              </span>
            )}
          </div>
        </div>
        {metric && (
          <span className="text-[11px] text-sibila-fog tabular-nums">{metric}</span>
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
