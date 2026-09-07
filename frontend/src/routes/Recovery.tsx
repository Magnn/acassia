import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { Sparkles, Clock, TrendingUp, ArrowRight, Inbox, AlertCircle } from 'lucide-react';
import { analyticsApi } from '../api/analytics';
import ScoreBadge from '../components/ScoreBadge';

export default function Recovery() {
  const { data, isLoading } = useQuery({
    queryKey: ['recovery-suggestions'],
    queryFn: analyticsApi.recoverySuggestions,
    refetchInterval: 60000,
  });

  const items = data?.items ?? [];
  const total = data?.total ?? 0;

  return (
    <div className="p-10 max-w-5xl mx-auto space-y-8">
      <div>
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-2xl bg-accent-amethyst/10 flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-accent-amethyst" />
          </div>
          <h1 className="text-3xl font-black tracking-tight">Recuperação</h1>
        </div>
        <p className="text-secondary text-sm font-medium">
          Leads que sumiram nos últimos {data?.criteria?.max_days_inactive || 30} dias e ainda
          podem voltar — priorizados pelo score.
        </p>
      </div>

      {/* Stats top */}
      <div className="grid grid-cols-3 gap-3">
        <StatCard
          icon={Inbox}
          label="Total recuperáveis"
          value={total}
          color="text-accent-amethyst"
        />
        <StatCard
          icon={TrendingUp}
          label="Hot inativos"
          value={items.filter(l => l.score_band === 'hot').length}
          color="text-red-500"
        />
        <StatCard
          icon={Clock}
          label="Dias médios"
          value={
            items.length > 0
              ? Math.round(items.reduce((acc, l) => acc + l.days_inactive, 0) / items.length)
              : 0
          }
          color="text-amber-500"
          suffix=" dias"
        />
      </div>

      {/* List */}
      {isLoading ? (
        <div className="text-secondary text-sm text-center py-12">Carregando...</div>
      ) : items.length === 0 ? (
        <div className="bg-bg-surface border border-dashed border-border rounded-3xl p-12 text-center">
          <Sparkles className="w-12 h-12 mx-auto text-secondary/40 mb-4" />
          <h3 className="font-black text-lg mb-2">Tudo em dia</h3>
          <p className="text-secondary text-sm">
            Nenhum lead na zona de recuperação agora. Continue atendendo!
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          <div className="flex items-center justify-between mb-3 px-1">
            <h3 className="text-sm font-black uppercase tracking-widest text-secondary">
              Leads esquentando esfriando
            </h3>
            <span className="text-[10px] text-secondary">
              Critério: {data?.criteria?.min_days_inactive}-{data?.criteria?.max_days_inactive}d sem msg
            </span>
          </div>
          {items.map((l) => (
            <Link
              key={l.id}
              to={`/leads?selected=${l.id}`}
              className="flex items-center justify-between gap-4 p-4 bg-bg-surface border border-border hover:border-accent-amethyst/30 rounded-2xl transition-all group"
            >
              <div className="flex items-center gap-4 min-w-0 flex-1">
                <ScoreBadge band={l.score_band as 'hot' | 'warm' | 'cold'} value={l.score_value} size="md" />
                <div className="min-w-0 flex-1">
                  <div className="font-black text-sm truncate">
                    {l.nome || l.telefone}
                  </div>
                  <div className="flex items-center gap-3 text-[11px] text-secondary mt-0.5">
                    <span className="font-mono">{l.telefone}</span>
                    <span>·</span>
                    <span className="capitalize">Nó: {l.node_atual}</span>
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-3 flex-shrink-0">
                <div className="text-right">
                  <div className="text-xs font-black flex items-center gap-1.5">
                    <AlertCircle className="w-3.5 h-3.5 text-amber-500" />
                    <span className="text-amber-500">{l.days_inactive}d sem msg</span>
                  </div>
                  <div className="text-[10px] text-secondary">
                    {l.last_msg_at ? new Date(l.last_msg_at).toLocaleDateString('pt-BR') : '—'}
                  </div>
                </div>
                <ArrowRight className="w-4 h-4 text-secondary group-hover:text-accent-amethyst" />
              </div>
            </Link>
          ))}
        </div>
      )}

      {/* Help footer */}
      <div className="bg-blue-500/5 border border-blue-500/20 rounded-3xl p-6 text-xs">
        <h3 className="font-black mb-2 flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-blue-400" />
          Como recuperar
        </h3>
        <ul className="space-y-1.5 text-secondary">
          <li>• Hot leads ({'>'}=70 pts): mandar mensagem direta com proposta de valor</li>
          <li>• Warm (40-69): retomar a conversa onde parou, lembrar do contexto</li>
          <li>• Cold ({'<'}40): mensagem suave e não-intrusiva, oferecer algo grátis</li>
        </ul>
      </div>
    </div>
  );
}

function StatCard({
  icon: Icon, label, value, color, suffix = '',
}: {
  icon: typeof Sparkles;
  label: string;
  value: number;
  color: string;
  suffix?: string;
}) {
  return (
    <div className="bg-bg-surface border border-border rounded-2xl p-4">
      <div className="flex items-center gap-2 mb-2">
        <Icon className={`w-3.5 h-3.5 ${color}`} />
        <span className="text-[9px] font-black uppercase tracking-widest text-secondary">{label}</span>
      </div>
      <div className="text-2xl font-black tracking-tight">{value.toLocaleString('pt-BR')}{suffix}</div>
    </div>
  );
}
