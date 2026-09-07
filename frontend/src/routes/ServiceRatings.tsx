import { useQuery } from '@tanstack/react-query';
import { ClipboardCheck, Star, TrendingUp, MessageSquare } from 'lucide-react';
import { api } from '../api/client';

export default function ServiceRatings() {
  const { data } = useQuery({
    queryKey: ['service-ratings'],
    queryFn: () => api.get<{
      ratings: { id: number; lead_id: number; lead_name: string; rating: number; feedback: string | null; context: string | null; created_at: string | null }[];
      average: number; nps_score: number; total: number;
      distribution: Record<string, number>;
    }>('/saas/atendimento/ratings'),
  });

  const starColors = ['', 'text-red-400', 'text-orange-400', 'text-amber-400', 'text-lime-400', 'text-emerald-400'];

  return (
    <div className="px-8 py-8 max-w-[1400px] mx-auto min-h-screen">
      <div className="flex items-center gap-3 mb-8">
        <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center shadow-lg">
          <ClipboardCheck className="w-6 h-6 text-white" />
        </div>
        <div>
          <h1 className="font-display text-3xl text-primary tracking-tight">Avaliações (NPS)</h1>
          <p className="text-xs text-secondary">{data?.total || 0} avaliações coletadas</p>
        </div>
      </div>

      {/* KPIs */}
      {data && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-bg-surface border border-border rounded-2xl p-5">
            <div className="text-xs text-secondary mb-1">Média</div>
            <div className="flex items-center gap-2">
              <span className="text-2xl font-bold text-primary">{data.average}</span>
              <div className="flex">{Array.from({ length: 5 }, (_, i) => (
                <Star key={i} className={`w-4 h-4 ${i < Math.round(data.average) ? 'text-amber-400 fill-amber-400' : 'text-secondary/20'}`} />
              ))}</div>
            </div>
          </div>
          <div className="bg-bg-surface border border-border rounded-2xl p-5">
            <div className="text-xs text-secondary mb-1">NPS Score</div>
            <div className={`text-2xl font-bold ${data.nps_score >= 50 ? 'text-emerald-400' : data.nps_score >= 0 ? 'text-amber-400' : 'text-rose-400'}`}>{data.nps_score}</div>
          </div>
          <div className="bg-bg-surface border border-border rounded-2xl p-5">
            <div className="text-xs text-secondary mb-1">Total Avaliações</div>
            <div className="text-2xl font-bold text-primary">{data.total}</div>
          </div>
          <div className="bg-bg-surface border border-border rounded-2xl p-5">
            <div className="text-xs text-secondary mb-2">Distribuição</div>
            <div className="space-y-1">
              {[5, 4, 3, 2, 1].map(n => {
                const count = data.distribution[n] || 0;
                const pct = data.total > 0 ? (count / data.total * 100) : 0;
                return (
                  <div key={n} className="flex items-center gap-2 text-[10px]">
                    <span className="w-3 font-bold text-primary">{n}</span>
                    <div className="flex-1 h-2 bg-bg-sidebar rounded overflow-hidden">
                      <div className={`h-full rounded ${n >= 4 ? 'bg-emerald-500' : n === 3 ? 'bg-amber-500' : 'bg-rose-500'}`} style={{ width: `${pct}%` }} />
                    </div>
                    <span className="w-6 text-right text-secondary">{count}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Rating List */}
      <div className="space-y-3">
        {(data?.ratings || []).map(r => (
          <div key={r.id} className="bg-bg-surface border border-border rounded-xl p-4 flex items-center gap-4">
            <div className="flex">{Array.from({ length: 5 }, (_, i) => (
              <Star key={i} className={`w-4 h-4 ${i < r.rating ? `${starColors[r.rating]} fill-current` : 'text-secondary/20'}`} />
            ))}</div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-bold text-primary">{r.lead_name}</div>
              {r.feedback && <div className="text-xs text-secondary truncate">"{r.feedback}"</div>}
            </div>
            {r.context && <span className="text-[9px] text-secondary bg-bg-sidebar px-2 py-0.5 rounded">{r.context}</span>}
            <div className="text-[10px] text-secondary">
              {r.created_at && new Date(r.created_at).toLocaleDateString('pt-BR')}
            </div>
          </div>
        ))}
        {(!data?.ratings?.length) && (
          <div className="text-center py-20 text-secondary">
            <Star className="w-12 h-12 mx-auto mb-4 opacity-30" />
            <p className="text-sm">Nenhuma avaliação recebida ainda.</p>
          </div>
        )}
      </div>
    </div>
  );
}
