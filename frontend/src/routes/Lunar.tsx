import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Moon, Sparkles, Calendar as CalendarIcon } from 'lucide-react';
import { api } from '../api/client';

interface LunarPhase {
  date: string;
  phase_name: 'nova' | 'crescente' | 'cheia' | 'minguante';
  illumination_pct: number;
  is_special: boolean;
  special_label: string | null;
  emoji: string;
}

interface NextOccurrence {
  phase: string;
  next_date: string;
  days_until: number;
}

const PHASE_LABELS: Record<string, string> = {
  nova: 'Lua Nova',
  crescente: 'Lua Crescente',
  cheia: 'Lua Cheia',
  minguante: 'Lua Minguante',
};

const PHASE_DESCRIPTIONS: Record<string, string> = {
  nova: 'Início, intenções, recomeços. Ideal pra trabalhos de início e plantio de sementes.',
  crescente: 'Crescimento, expansão, manifestação. Ideal pra atrair prosperidade e novos amores.',
  cheia: 'Pico de energia, manifestação completa. Ideal pra rituais de gratidão e poder máximo.',
  minguante: 'Liberação, limpeza, desapego. Ideal pra cortar laços e remover bloqueios.',
};

export default function Lunar() {
  const [monthOffset, setMonthOffset] = useState(0);

  const { data: today } = useQuery({
    queryKey: ['lunar-today'],
    queryFn: () => api.get<LunarPhase>('/saas/lunar/today'),
  });

  // Range: mês atual + offset
  const fromDt = new Date();
  fromDt.setMonth(fromDt.getMonth() + monthOffset, 1);
  fromDt.setHours(0, 0, 0, 0);
  const toDt = new Date(fromDt);
  toDt.setMonth(toDt.getMonth() + 1, 0);

  const { data: cal, isLoading } = useQuery({
    queryKey: ['lunar-calendar', monthOffset],
    queryFn: () =>
      api.get<{ items: LunarPhase[] }>(
        `/saas/lunar/calendar?from=${fmtDate(fromDt)}&to=${fmtDate(toDt)}`,
      ),
  });

  const phases = cal?.items ?? [];

  // Próximas fases
  const phaseQueries = (['nova', 'crescente', 'cheia', 'minguante'] as const).map(p =>
    useQuery({
      queryKey: ['lunar-next', p],
      queryFn: () => api.get<NextOccurrence>(`/saas/lunar/next/${p}`),
    }),
  );

  return (
    <div className="p-10 max-w-5xl mx-auto space-y-8">
      <div>
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-2xl bg-accent-amethyst/10 flex items-center justify-center">
            <Moon className="w-5 h-5 text-accent-amethyst" />
          </div>
          <h1 className="text-3xl font-black tracking-tight">Calendário Lunar</h1>
        </div>
        <p className="text-secondary text-sm font-medium">
          Fases da lua pra agendar tiragens, rituais e broadcasts no momento certo.
        </p>
      </div>

      {/* Hoje */}
      {today && (
        <div className="bg-gradient-to-br from-purple-900/30 to-indigo-900/20 border border-accent-amethyst/30 rounded-3xl p-8 text-center space-y-4">
          <div className="text-7xl">{today.emoji}</div>
          <div>
            <div className="text-xs uppercase tracking-widest text-accent-amethyst font-black mb-1">
              Hoje
            </div>
            <h2 className="text-2xl font-black tracking-tight">{PHASE_LABELS[today.phase_name]}</h2>
            <p className="text-sm text-secondary mt-1">
              {today.illumination_pct}% iluminada
            </p>
          </div>
          <p className="text-xs text-secondary max-w-md mx-auto leading-relaxed">
            {PHASE_DESCRIPTIONS[today.phase_name]}
          </p>
          {today.is_special && today.special_label && (
            <div className="inline-flex items-center gap-2 bg-amber-500/10 border border-amber-500/30 px-3 py-1.5 rounded-full text-xs font-black text-amber-400 uppercase tracking-widest">
              <Sparkles className="w-3 h-3" />
              {today.special_label}
            </div>
          )}
        </div>
      )}

      {/* Próximas fases */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {phaseQueries.map(({ data }, i) => {
          const phase = (['nova', 'crescente', 'cheia', 'minguante'] as const)[i];
          if (!data) return <div key={phase} className="h-24 bg-bg-surface rounded-2xl animate-pulse" />;
          return (
            <div
              key={phase}
              className="bg-bg-surface border border-border rounded-2xl p-4"
            >
              <div className="text-2xl mb-1">
                {phase === 'nova' ? '🌑' : phase === 'crescente' ? '🌒' : phase === 'cheia' ? '🌕' : '🌖'}
              </div>
              <div className="text-[10px] font-black uppercase tracking-widest text-secondary">
                Próxima {PHASE_LABELS[phase]}
              </div>
              <div className="text-sm font-black mt-1">{fmtPtBr(data.next_date)}</div>
              <div className="text-[10px] text-accent-amethyst mt-0.5">
                em {data.days_until} dia{data.days_until !== 1 ? 's' : ''}
              </div>
            </div>
          );
        })}
      </div>

      {/* Calendar grid */}
      <div className="bg-bg-surface border border-border rounded-3xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-black flex items-center gap-2">
            <CalendarIcon className="w-4 h-4 text-accent-amethyst" />
            {fromDt.toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' })}
          </h3>
          <div className="flex gap-2">
            <button
              onClick={() => setMonthOffset(o => o - 1)}
              className="px-3 py-1.5 bg-bg-primary border border-border hover:border-accent-amethyst/30 rounded-lg text-xs font-bold"
            >
              ‹ Anterior
            </button>
            {monthOffset !== 0 && (
              <button
                onClick={() => setMonthOffset(0)}
                className="px-3 py-1.5 bg-accent-amethyst/10 border border-accent-amethyst/30 text-accent-amethyst rounded-lg text-xs font-bold"
              >
                Hoje
              </button>
            )}
            <button
              onClick={() => setMonthOffset(o => o + 1)}
              className="px-3 py-1.5 bg-bg-primary border border-border hover:border-accent-amethyst/30 rounded-lg text-xs font-bold"
            >
              Próximo ›
            </button>
          </div>
        </div>

        {isLoading ? (
          <div className="text-center py-8 text-secondary text-sm">Carregando fases...</div>
        ) : (
          <div className="grid grid-cols-7 gap-1">
            {/* Header dias da semana */}
            {['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'].map((d) => (
              <div key={d} className="text-center text-[10px] font-black uppercase tracking-widest text-secondary py-2">
                {d}
              </div>
            ))}
            {/* Padding do início */}
            {phases.length > 0 && Array.from({
              length: new Date(phases[0].date + 'T00:00:00').getDay(),
            }).map((_, i) => (
              <div key={`pad-${i}`} className="aspect-square" />
            ))}
            {/* Dias */}
            {phases.map((p) => {
              const day = parseInt(p.date.split('-')[2], 10);
              const isToday = p.date === today?.date;
              return (
                <div
                  key={p.date}
                  className={`aspect-square rounded-xl flex flex-col items-center justify-center text-center ${
                    isToday ? 'bg-accent-amethyst/20 border-2 border-accent-amethyst' :
                    p.is_special ? 'bg-amber-500/5 border border-amber-500/30' :
                    'bg-bg-primary border border-border'
                  }`}
                  title={`${PHASE_LABELS[p.phase_name]} · ${p.illumination_pct}%`}
                >
                  <div className="text-xl">{p.emoji}</div>
                  <div className="text-[10px] font-black mt-0.5">{day}</div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Tip */}
      <div className="bg-blue-500/5 border border-blue-500/20 rounded-3xl p-6 space-y-2 text-xs">
        <h3 className="font-black flex items-center gap-2">
          <Sparkles className="w-3.5 h-3.5 text-blue-400" />
          Dica de uso
        </h3>
        <p className="text-secondary leading-relaxed">
          Use o calendário pra agendar broadcasts em <strong className="text-blue-400">lua cheia</strong> (pico
          de energia, perfeito pra promoções). Em <strong className="text-blue-400">lua nova</strong>, mande
          mensagens de novos começos. Próximo: nó "gatilho lunar" no Builder pra automatizar (Frente 4.2).
        </p>
      </div>
    </div>
  );
}

function fmtDate(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function fmtPtBr(iso: string): string {
  const [y, m, d] = iso.split('-').map(Number);
  const date = new Date(y, m - 1, d);
  return date.toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' });
}
