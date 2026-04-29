import { useQuery } from '@tanstack/react-query';
import { metricsApi } from '../api/metrics';
import { Activity, Users, CheckCircle, PauseCircle } from 'lucide-react';

export default function Dashboard() {
  const { data: kpis, isLoading, error } = useQuery({
    queryKey: ['saas-metrics'],
    queryFn: metricsApi.get,
    refetchInterval: 30000, // Atualiza a cada 30s
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

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <h2 className="text-2xl font-bold mb-6 font-display tracking-tight text-white">Dashboard</h2>
      
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-cigana-surface border border-cigana-border rounded-xl p-5 shadow-sm hover:border-cigana-purple/40 transition-colors">
          <div className="flex items-center justify-between mb-3">
            <div className="text-xs text-slate-400 uppercase tracking-widest font-semibold">Total Leads</div>
            <Users className="w-4 h-4 text-slate-500" />
          </div>
          <div className="text-3xl font-bold text-slate-100 mb-1">{kpis.total_leads}</div>
          <div className="text-[11px] text-slate-500">Histórico completo</div>
        </div>

        <div className="bg-cigana-surface border border-cigana-border rounded-xl p-5 shadow-sm hover:border-cigana-purple/40 transition-colors">
          <div className="flex items-center justify-between mb-3">
            <div className="text-xs text-slate-400 uppercase tracking-widest font-semibold">Leads (7d)</div>
            <Activity className="w-4 h-4 text-sky-400" />
          </div>
          <div className="text-3xl font-bold text-slate-100 mb-1">{kpis.leads_7d}</div>
          <div className="text-[11px] text-slate-500">{kpis.leads_30d} nos últimos 30d</div>
        </div>

        <div className="bg-cigana-surface border border-cigana-border rounded-xl p-5 shadow-sm hover:border-emerald-500/40 transition-colors">
          <div className="flex items-center justify-between mb-3">
            <div className="text-xs text-slate-400 uppercase tracking-widest font-semibold">Convertidos</div>
            <CheckCircle className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-3xl font-bold text-emerald-400 mb-1">{kpis.convertidos}</div>
          <div className="text-[11px] text-slate-500 font-medium bg-emerald-400/10 text-emerald-400 inline-block px-1.5 py-0.5 rounded">
            {kpis.conversion_rate}% taxa
          </div>
        </div>

        <div className="bg-cigana-surface border border-cigana-border rounded-xl p-5 shadow-sm hover:border-cigana-purple/40 transition-colors">
          <div className="flex items-center justify-between mb-3">
            <div className="text-xs text-slate-400 uppercase tracking-widest font-semibold">Ativas</div>
            <PauseCircle className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-3xl font-bold text-slate-100 mb-1">{kpis.ativas}</div>
          <div className="text-[11px] text-slate-500">
            {kpis.pausadas} pausadas · {kpis.opt_out} opt-out
          </div>
        </div>
      </div>

      <div className="bg-cigana-surface border border-cigana-border rounded-xl p-6 shadow-sm">
        <h3 className="font-bold mb-4 text-slate-200">Distribuição no Funil (Top 5)</h3>
        {kpis.node_distribution && kpis.node_distribution.length > 0 ? (
          <div className="space-y-4">
            {kpis.node_distribution.map((nd, idx) => {
              const maxCount = kpis.node_distribution[0].count;
              const width = maxCount > 0 ? Math.round((nd.count / maxCount) * 100) : 0;
              
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
          <p className="text-sm text-slate-500 italic">Sem dados no funil ainda.</p>
        )}
      </div>
    </div>
  );
}
