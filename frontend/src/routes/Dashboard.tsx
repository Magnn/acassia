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
import { Activity, CheckCircle2, DollarSign, PauseCircle, Users, TrendingUp, Sparkles, PhoneCall } from 'lucide-react';
import { metricsApi } from '../api/metrics';
import LaunchChecklist from '../components/LaunchChecklist';

const CHART = {
  amethyst: '#818cf8',
  ember: '#10b981',
  rose: '#f43f5e',
  grid: 'rgba(255, 255, 255, 0.06)',
  axis: 'rgba(255, 255, 255, 0.4)',
};

export default function Dashboard() {
  const { data: kpis, isLoading, error } = useQuery({
    queryKey: ['saas-metrics'],
    queryFn: metricsApi.get,
    staleTime: 5 * 60_000,
    refetchInterval: 5 * 60_000,
  });

  const { data: exec } = useQuery({
    queryKey: ['executive-kpis', 7],
    queryFn: () => metricsApi.getExecutive(7),
    staleTime: 5 * 60_000,
    refetchInterval: 5 * 60_000,
  });

  if (isLoading) {
    return (
      <div className="p-12 max-w-7xl mx-auto flex flex-col items-center justify-center min-h-[400px]">
        <div className="w-12 h-12 border-4 border-[#25D366]/20 border-t-[#25D366] rounded-full animate-spin mb-4" />
        <div className="text-secondary text-xs font-bold uppercase tracking-widest animate-pulse">
          Consolidando métricas e conversões do WhatsApp…
        </div>
      </div>
    );
  }

  if (error || !kpis) {
    return (
      <div className="p-8 max-w-6xl mx-auto space-y-6">
        <LaunchChecklist />
        <div className="bg-red-500/10 border border-red-500/30 text-red-400 rounded-3xl p-8 text-center">
          <div className="font-bold text-lg mb-1">Falha ao carregar métricas</div>
          <div className="text-xs opacity-80">{(error as Error)?.message || 'Erro desconhecido'}</div>
        </div>
      </div>
    );
  }

  const series = (exec?.series ?? []).map((p) => ({
    ...p,
    label: p.date.slice(5),
  }));

  return (
    <div className="px-6 sm:px-8 py-8 max-w-6xl mx-auto space-y-8 text-primary">
      {/* ═══ HEADER ═══ */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-6">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">
              Visão Geral
            </h1>
            <div className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/25 text-emerald-400 text-[10px] font-bold">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              Tempo Real
            </div>
          </div>
          <p className="text-xs text-secondary mt-1 max-w-2xl">
            Acompanhe a movimentação dos contatos no funil, conversões de vendas e saúde financeira da sua operação.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div className="px-3.5 py-1.5 rounded-xl bg-bg-surface border border-border text-xs flex items-center gap-2">
            <PhoneCall className="w-3.5 h-3.5 text-[#25D366]" />
            <span className="text-secondary">Canal principal:</span>
            <strong className="text-primary font-medium">WhatsApp</strong>
          </div>
        </div>
      </div>

      {/* Checklist Onboarding */}
      <LaunchChecklist />

      {/* ═══ KPI CARDS ═══ */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          label="Total de Leads"
          value={kpis.total_leads}
          hint="Histórico total acumulado"
          Icon={Users}
          color="from-blue-500/10 to-indigo-500/5"
          border="border-blue-500/20"
          accent="text-blue-400"
        />
        <KpiCard
          label="Leads (7 dias)"
          value={kpis.leads_7d}
          hint={`${kpis.leads_30d} nos últimos 30 dias`}
          Icon={Activity}
          color="from-purple-500/10 to-violet-500/5"
          border="border-purple-500/20"
          accent="text-purple-400"
        />
        <KpiCard
          label="Vendas Confirmadas"
          value={kpis.convertidos}
          hint={`${kpis.conversion_rate}% de conversão`}
          Icon={CheckCircle2}
          color="from-emerald-500/15 to-[#25D366]/5"
          border="border-emerald-500/30"
          accent="text-emerald-400"
          valueAccent="text-emerald-400"
        />
        <KpiCard
          label="Sessões Ativas"
          value={kpis.ativas}
          hint={`${kpis.pausadas} em pausa · ${kpis.opt_out} saídas`}
          Icon={PauseCircle}
          color="from-amber-500/10 to-orange-500/5"
          border="border-amber-500/20"
          accent="text-amber-400"
        />
      </div>

      {/* ═══ GRÁFICOS FINANCEIROS E CONVERSÕES ═══ */}
      {exec && series.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Panel
            title="Performance Financeira"
            subtitle="Receita vs Lucro (7 dias)"
            Icon={DollarSign}
            iconAccent="text-emerald-400"
            metric={`Hoje: ${brl(exec.revenue_today ?? 0)}`}
          >
            <div className="h-[260px] mt-4">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={series} margin={{ top: 10, right: 10, left: -15, bottom: 0 }}>
                  <defs>
                    <linearGradient id="revGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={CHART.ember} stopOpacity={0.25} />
                      <stop offset="100%" stopColor={CHART.ember} stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="profGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={CHART.amethyst} stopOpacity={0.2} />
                      <stop offset="100%" stopColor={CHART.amethyst} stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke={CHART.grid} strokeDasharray="3 3" vertical={false} />
                  <XAxis
                    dataKey="label"
                    stroke={CHART.axis}
                    fontSize={11}
                    tickLine={false}
                    axisLine={false}
                    dy={8}
                  />
                  <YAxis
                    stroke={CHART.axis}
                    fontSize={11}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(v) => `R$${v}`}
                  />
                  <Tooltip
                    contentStyle={tooltipStyle}
                    formatter={(v: number) => brl(v)}
                    cursor={{ stroke: 'rgba(255, 255, 255, 0.1)', strokeWidth: 1 }}
                  />
                  <Area
                    type="monotone"
                    dataKey="revenue_brl"
                    stroke={CHART.ember}
                    fill="url(#revGrad)"
                    strokeWidth={2.5}
                    name="Receita"
                    animationDuration={1200}
                  />
                  <Area
                    type="monotone"
                    dataKey="profit_brl"
                    stroke={CHART.amethyst}
                    fill="url(#profGrad)"
                    strokeWidth={2}
                    strokeDasharray="4 4"
                    name="Lucro"
                    animationDuration={1500}
                  />
                  <Legend
                    wrapperStyle={{ fontSize: 11, fontWeight: 'bold', paddingTop: 16 }}
                    iconType="circle"
                    iconSize={8}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </Panel>

          <Panel
            title="Volume de Conversões"
            subtitle="Checkout confirmados"
            Icon={TrendingUp}
            iconAccent="text-indigo-400"
            metric={`Hoje: ${exec.sales_count_today ?? 0} vendas`}
          >
            <div className="h-[260px] mt-4">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={series} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid stroke={CHART.grid} strokeDasharray="3 3" vertical={false} />
                  <XAxis
                    dataKey="label"
                    stroke={CHART.axis}
                    fontSize={11}
                    tickLine={false}
                    axisLine={false}
                    dy={8}
                  />
                  <YAxis
                    stroke={CHART.axis}
                    fontSize={11}
                    tickLine={false}
                    axisLine={false}
                    allowDecimals={false}
                  />
                  <Tooltip
                    contentStyle={tooltipStyle}
                    cursor={{ fill: 'rgba(255, 255, 255, 0.03)' }}
                  />
                  <Bar
                    dataKey="transactions_count"
                    fill={CHART.amethyst}
                    radius={[6, 6, 0, 0]}
                    name="Vendas"
                    barSize={28}
                    animationDuration={1200}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Panel>
        </div>
      )}

      {/* ═══ FUNIL DE CONTATOS ═══ */}
      <Panel
        title="Distribuição por Etapa do Funil"
        subtitle="Posição atual dos leads cadastrados"
        Icon={Sparkles}
        iconAccent="text-purple-400"
      >
        {kpis.node_distribution && kpis.node_distribution.length > 0 ? (
          <div className="grid gap-3.5 mt-6">
            {kpis.node_distribution.map((nd, idx) => {
              const maxCount = kpis.node_distribution[0].count;
              const width = maxCount > 0 ? Math.round((nd.count / maxCount) * 100) : 0;
              return (
                <div key={idx} className="group">
                  <div className="flex justify-between items-end text-xs mb-1.5">
                    <span className="font-bold text-primary opacity-80 group-hover:opacity-100 transition-opacity">
                      {nd.node}
                    </span>
                    <span className="font-mono font-bold text-indigo-400 text-xs">
                      {nd.count} leads ({width}%)
                    </span>
                  </div>
                  <div className="w-full h-2.5 bg-bg-primary rounded-full overflow-hidden border border-border p-0.5">
                    <div
                      className="h-full bg-gradient-to-r from-indigo-500 to-emerald-400 rounded-full transition-all duration-1000 ease-out shadow-sm"
                      style={{ width: `${Math.max(width, 2)}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="py-12 text-center text-xs text-secondary italic">
            Nenhum contato ativo em etapas no momento. Leads novos aparecerão aqui automaticamente.
          </div>
        )}
      </Panel>
    </div>
  );
}

const tooltipStyle = {
  backgroundColor: '#18181b',
  border: '1px solid rgba(255, 255, 255, 0.1)',
  borderRadius: '12px',
  padding: '10px 14px',
  fontSize: '12px',
  color: '#f4f4f5',
  boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.5)',
};

function KpiCard({
  label,
  value,
  hint,
  Icon,
  color = 'from-bg-surface to-bg-surface',
  border = 'border-border',
  accent = 'text-secondary',
  valueAccent = 'text-primary',
}: {
  label: string;
  value: number;
  hint: string;
  Icon: typeof Users;
  color?: string;
  border?: string;
  accent?: string;
  valueAccent?: string;
}) {
  return (
    <div
      className={`bg-gradient-to-br ${color} bg-bg-surface border ${border} rounded-3xl p-5 hover:shadow-lg transition-all group overflow-hidden relative`}
    >
      <div className="flex items-center justify-between mb-3">
        <span className="text-[11px] text-secondary font-bold uppercase tracking-wider">
          {label}
        </span>
        <div className={`p-2 rounded-xl bg-bg-primary/80 border border-border/50 ${accent}`}>
          <Icon className="w-4 h-4" />
        </div>
      </div>
      <div className={`font-mono font-black text-3xl leading-none tracking-tight ${valueAccent} tabular-nums`}>
        {value}
      </div>
      <div className="text-[10px] text-secondary mt-3 flex items-center gap-1.5">
        <span className="w-1.5 h-1.5 rounded-full bg-border" />
        {hint}
      </div>
    </div>
  );
}

function Panel({
  title,
  subtitle,
  Icon,
  iconAccent = 'text-indigo-400',
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
    <section className="bg-bg-surface border border-border rounded-3xl p-6 sm:p-7 shadow-sm">
      <header className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-3">
          {Icon && (
            <div className={`p-2.5 rounded-2xl bg-bg-primary border border-border ${iconAccent}`}>
              <Icon className="w-4 h-4" />
            </div>
          )}
          <div>
            <h3 className="font-bold text-base text-primary leading-snug">
              {title}
            </h3>
            {subtitle && (
              <span className="text-[11px] text-secondary block mt-0.5">
                {subtitle}
              </span>
            )}
          </div>
        </div>
        {metric && (
          <div className="bg-bg-primary px-3 py-1 rounded-full border border-border">
            <span className="text-xs font-mono font-bold text-primary">{metric}</span>
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
