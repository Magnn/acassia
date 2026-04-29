import {
  User, MapPin, Calendar, Sparkles, MessageSquare,
  TrendingUp, TrendingDown, Activity, Star, CreditCard,
  Wand2, Phone,
} from 'lucide-react';
import { useLeadContext } from '../hooks/useLeadContext';
import ScoreBadge from './ScoreBadge';

interface Props {
  leadId: number | null;
}

export default function LeadContextPanel({ leadId }: Props) {
  const { data, isLoading } = useLeadContext(leadId);

  if (!leadId) {
    return (
      <div className="p-6 text-center text-secondary text-sm">
        Selecione um lead pra ver o contexto
      </div>
    );
  }

  if (isLoading || !data) {
    return (
      <div className="p-6 space-y-4 animate-pulse">
        <div className="h-32 bg-bg-surface rounded-2xl" />
        <div className="h-24 bg-bg-surface rounded-2xl" />
        <div className="h-24 bg-bg-surface rounded-2xl" />
      </div>
    );
  }

  const { lead, score, journey, sentiment, commercial, tarot_readings_count } = data;

  return (
    <div className="p-4 space-y-3 overflow-y-auto h-full">
      {/* Lead card */}
      <Card title="Lead" icon={User}>
        <KV k="Nome" v={lead.nome || '—'} />
        <KV k="Telefone" v={lead.telefone} icon={Phone} />
        {lead.signo && <KV k="Signo" v={lead.signo} icon={Star} />}
        {lead.idade && <KV k="Idade" v={`${lead.idade} anos`} icon={Calendar} />}
        {lead.cidade && <KV k="Cidade" v={lead.cidade} icon={MapPin} />}
        {lead.criado_em && (
          <KV k="Cliente desde" v={new Date(lead.criado_em).toLocaleDateString('pt-BR')} />
        )}
        {lead.tags && lead.tags.length > 0 && (
          <div className="pt-2 mt-2 border-t border-border">
            <div className="text-[9px] font-black uppercase tracking-widest text-secondary mb-1.5">Tags</div>
            <div className="flex flex-wrap gap-1">
              {lead.tags.map((t, i) => (
                <span
                  key={`${t}-${i}`}
                  className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${
                    t === 'opted_out'
                      ? 'bg-red-500/10 text-red-400 border border-red-500/30'
                      : 'bg-bg-primary text-secondary border border-border'
                  }`}
                >
                  {t}
                </span>
              ))}
            </div>
          </div>
        )}
      </Card>

      {/* Score */}
      <Card title="Score" icon={Activity}>
        <div className="flex items-center justify-between">
          <ScoreBadge band={score.band} value={score.value} size="md" showValue />
          <div className="text-2xl font-black tracking-tight">{score.value}</div>
        </div>
        {score.components && Object.keys(score.components).length > 0 && (
          <div className="space-y-1.5 mt-3 pt-3 border-t border-border">
            {Object.entries(score.components).map(([k, v]) => (
              <div key={k} className="flex items-center gap-2">
                <span className="text-[10px] text-secondary capitalize w-20">{k}</span>
                <div className="flex-1 h-1 bg-bg-primary rounded-full overflow-hidden">
                  <div
                    className="h-full bg-accent-amethyst"
                    style={{ width: `${v}%` }}
                  />
                </div>
                <span className="text-[10px] font-mono w-8 text-right">{v}</span>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Jornada */}
      <Card title="Jornada" icon={Sparkles}>
        {journey.node_atual && (
          <KV k="Nó atual" v={journey.node_atual} />
        )}
        <KV k="Profundidade" v={`${journey.depth} nós`} />
        {journey.time_in_node_s !== null && (
          <KV k="No nó há" v={fmtDuration(journey.time_in_node_s)} />
        )}
        {journey.last_msg_at && (
          <KV k="Última msg" v={fmtRelative(journey.last_msg_at)} />
        )}
        <div className="flex flex-wrap gap-1.5 mt-2 pt-2 border-t border-border">
          {journey.convertido && (
            <span className="px-2 py-0.5 bg-emerald-500/10 text-emerald-500 text-[9px] font-black uppercase tracking-widest rounded border border-emerald-500/30">
              ✓ Convertido
            </span>
          )}
          {journey.bot_pausado && (
            <span className="px-2 py-0.5 bg-amber-500/10 text-amber-500 text-[9px] font-black uppercase tracking-widest rounded border border-amber-500/30">
              ⏸ Bot pausado
            </span>
          )}
          {journey.opt_out && (
            <span className="px-2 py-0.5 bg-red-500/10 text-red-500 text-[9px] font-black uppercase tracking-widest rounded border border-red-500/30">
              ✗ Opt-out
            </span>
          )}
        </div>
      </Card>

      {/* Sentimento */}
      <Card title="Sentimento" icon={MessageSquare}>
        <div className="flex items-center justify-between mb-2">
          <span className="text-[10px] text-secondary">Últimas 10 msgs:</span>
          <SentimentTrend trend={sentiment.trend} />
        </div>
        <div className="flex gap-1">
          {sentiment.recent.length === 0 ? (
            <span className="text-[11px] text-secondary">Sem dados</span>
          ) : (
            sentiment.recent.map((s, i) => (
              <div
                key={i}
                className={`w-2.5 h-2.5 rounded-full ${
                  s === 'pos' ? 'bg-emerald-500' :
                  s === 'neg' ? 'bg-red-500' :
                  'bg-zinc-600'
                }`}
                title={s}
              />
            ))
          )}
        </div>
        <div className="flex justify-between text-[10px] mt-2">
          <span className="text-emerald-500">+{sentiment.positive_count}</span>
          <span className="text-red-500">−{sentiment.negative_count}</span>
        </div>
      </Card>

      {/* Comercial */}
      <Card title="Comercial" icon={CreditCard}>
        <KV k="Pagamentos" v={String(commercial.payments_count)} />
        {commercial.payments.length > 0 && (
          <div className="mt-2 pt-2 border-t border-border space-y-1">
            {commercial.payments.slice(0, 3).map((p) => (
              <div key={p.id} className="flex items-center justify-between text-[10px]">
                <span className="font-mono text-secondary">{p.provider}</span>
                <span className="text-primary">
                  {p.processed_at && new Date(p.processed_at).toLocaleDateString('pt-BR')}
                </span>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Tarot count */}
      {tarot_readings_count > 0 && (
        <Card title="Tarot" icon={Wand2}>
          <KV k="Tiragens feitas" v={String(tarot_readings_count)} />
        </Card>
      )}
    </div>
  );
}

function Card({
  title, icon: Icon, children,
}: {
  title: string;
  icon: typeof User;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-bg-surface border border-border rounded-2xl p-4">
      <div className="flex items-center gap-2 mb-2.5 pb-2 border-b border-border">
        <Icon className="w-3.5 h-3.5 text-accent-amethyst" />
        <span className="text-[10px] font-black uppercase tracking-widest text-secondary">{title}</span>
      </div>
      <div className="space-y-1.5">{children}</div>
    </div>
  );
}

function KV({
  k, v, icon: Icon,
}: {
  k: string;
  v: string;
  icon?: typeof User;
}) {
  return (
    <div className="flex items-center justify-between gap-2 text-[11px]">
      <span className="text-secondary flex items-center gap-1.5">
        {Icon && <Icon className="w-2.5 h-2.5" />}
        {k}
      </span>
      <span className="text-primary font-bold truncate max-w-[55%]" title={v}>{v}</span>
    </div>
  );
}

function SentimentTrend({ trend }: { trend: 'positive' | 'negative' | 'neutral' }) {
  if (trend === 'positive') {
    return (
      <span className="text-emerald-500 flex items-center gap-1 text-[10px] font-bold">
        <TrendingUp className="w-3 h-3" /> POSITIVO
      </span>
    );
  }
  if (trend === 'negative') {
    return (
      <span className="text-red-500 flex items-center gap-1 text-[10px] font-bold">
        <TrendingDown className="w-3 h-3" /> NEGATIVO
      </span>
    );
  }
  return <span className="text-secondary text-[10px] font-bold">Neutro</span>;
}

function fmtDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}min`;
  if (seconds < 86400) return `${Math.round(seconds / 3600)}h`;
  return `${Math.round(seconds / 86400)}d`;
}

function fmtRelative(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const min = Math.floor(diff / 60000);
  if (min < 1) return 'agora';
  if (min < 60) return `${min}min atrás`;
  const h = Math.floor(min / 60);
  if (h < 24) return `${h}h atrás`;
  return `${Math.floor(h / 24)}d atrás`;
}
