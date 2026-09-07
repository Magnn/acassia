import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Wand2, RefreshCw, ArrowRight, Sparkles, Repeat } from 'lucide-react';
import { tarotApi } from '../api/tarot';

interface Props {
  leadId: number;
}

export default function TarotTrendsCard({ leadId }: Props) {
  const [showAi, setShowAi] = useState(false);

  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['tarot-trends', leadId, showAi],
    queryFn: () => tarotApi.cardTrends(leadId, { ai: showAi }),
  });

  if (isLoading || !data) return null;
  if (data.total_readings === 0) return null;

  const trajectory = data.trajectory;

  return (
    <div className="bg-bg-surface border border-border rounded-2xl p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-[10px] font-black uppercase tracking-widest text-secondary flex items-center gap-1.5">
          <Wand2 className="w-3 h-3 text-accent-amethyst" />
          Tendências do tarot
        </h3>
        <span className="text-[10px] text-secondary">
          {data.total_readings} tiragem{data.total_readings === 1 ? '' : 's'}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-2 text-[11px]">
        <div className="bg-bg-primary border border-border rounded-lg p-2 text-center">
          <div className="text-[9px] uppercase tracking-widest text-secondary">Cartas</div>
          <div className="text-base font-black tabular-nums">{data.total_cards_drawn}</div>
        </div>
        <div className="bg-bg-primary border border-border rounded-lg p-2 text-center">
          <div className="text-[9px] uppercase tracking-widest text-secondary">Invertidas</div>
          <div className="text-base font-black tabular-nums">{data.reversed_pct}%</div>
        </div>
        <div className="bg-bg-primary border border-border rounded-lg p-2 text-center">
          <div className="text-[9px] uppercase tracking-widest text-secondary">Maiores</div>
          <div className="text-base font-black tabular-nums">{data.arcana_distribution.major || 0}</div>
        </div>
      </div>

      {data.top_cards.length > 0 && (
        <div>
          <div className="text-[9px] font-black uppercase tracking-widest text-secondary mb-1.5">
            Mais frequentes
          </div>
          <div className="space-y-1">
            {data.top_cards.slice(0, 5).map((c) => (
              <div key={c.name} className="flex items-center gap-2 text-[11px]">
                <div className="flex-1 truncate font-bold">{c.name}</div>
                <div className="flex-1 max-w-[80px] h-1 bg-bg-primary rounded-full overflow-hidden">
                  <div
                    className="h-full bg-accent-amethyst"
                    style={{ width: `${c.pct}%` }}
                  />
                </div>
                <div className="text-[10px] text-secondary tabular-nums w-8 text-right">
                  {c.count}x
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {data.recurring_cards.length > 0 && (
        <div className="bg-accent-amethyst/5 border border-accent-amethyst/30 rounded-lg p-2">
          <div className="flex items-center gap-1.5 mb-1">
            <Repeat className="w-3 h-3 text-accent-amethyst" />
            <span className="text-[9px] uppercase font-black tracking-widest text-accent-amethyst">
              Tema recorrente
            </span>
          </div>
          <div className="text-[11px] text-primary leading-relaxed">
            {data.recurring_cards.map((c) => (
              <span key={c.name} className="font-bold">
                {c.name} ({c.count}x){' '}
              </span>
            ))}
          </div>
        </div>
      )}

      {trajectory && (
        <div className="bg-bg-primary border border-border rounded-lg p-2.5">
          <div className="text-[9px] uppercase font-black tracking-widest text-secondary mb-1.5">
            Trajetória (última tiragem)
          </div>
          <div className="flex items-center gap-2 text-[11px]">
            <div className="flex-1 truncate">
              <div className="font-bold">{trajectory.from}</div>
              <div className="text-[9px] text-secondary">
                passado {trajectory.from_reversed && '(inv)'}
              </div>
            </div>
            <ArrowRight className="w-3 h-3 text-accent-amethyst flex-shrink-0" />
            <div className="flex-1 truncate text-right">
              <div className="font-bold">{trajectory.to}</div>
              <div className="text-[9px] text-secondary">
                futuro {trajectory.to_reversed && '(inv)'}
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="border-t border-border pt-2 space-y-2">
        {data.ai_insight ? (
          <>
            <div className="bg-bg-primary border border-border rounded-lg p-2.5">
              <div className="text-[9px] uppercase font-black tracking-widest text-secondary mb-1 flex items-center gap-1">
                <Sparkles className="w-2.5 h-2.5" />
                Insight IA
              </div>
              <p className="text-[11px] leading-relaxed">{data.ai_insight}</p>
            </div>
            <button
              onClick={() => refetch()}
              disabled={isFetching}
              className="text-[10px] text-accent-amethyst hover:underline flex items-center gap-1 font-bold"
            >
              <RefreshCw className={`w-3 h-3 ${isFetching ? 'animate-spin' : ''}`} />
              Regenerar
            </button>
          </>
        ) : (
          <button
            onClick={() => setShowAi(true)}
            disabled={isFetching}
            className="w-full px-3 py-1.5 bg-bg-primary border border-border hover:border-accent-amethyst/30 disabled:opacity-30 rounded-lg text-[11px] font-bold flex items-center justify-center gap-1.5"
          >
            <Sparkles className="w-3 h-3 text-accent-amethyst" />
            {isFetching ? 'Pensando…' : 'Gerar insight IA'}
          </button>
        )}
      </div>
    </div>
  );
}
