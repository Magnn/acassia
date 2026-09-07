import { useMemo, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  CalendarDays, Sparkles, Wand2, RefreshCw, Plus, X, Trash2, Copy, Check,
  ChevronLeft, ChevronRight, Moon,
} from 'lucide-react';
import {
  calendarApi,
  type SpiritualEvent,
  type SpiritualTradition,
} from '../api/calendar';
import { handleApiError } from '../lib/handleApiError';
import { toast } from '../lib/toast';

const TRADITIONS: { key: SpiritualTradition; label: string; emoji: string; color: string }[] = [
  { key: 'crista', label: 'Cristã', emoji: '✝', color: 'border-amber-400/40 text-amber-300' },
  { key: 'afro', label: 'Afro-brasileira', emoji: '🌊', color: 'border-cyan-400/40 text-cyan-300' },
  { key: 'paga', label: 'Pagã', emoji: '🍃', color: 'border-emerald-400/40 text-emerald-300' },
  { key: 'astronomica', label: 'Astronômica', emoji: '🌙', color: 'border-indigo-400/40 text-indigo-300' },
  { key: 'secular', label: 'Secular', emoji: '✦', color: 'border-rose-400/40 text-rose-300' },
];

const TRADITION_META = TRADITIONS.reduce<Record<string, typeof TRADITIONS[number]>>(
  (acc, t) => { acc[t.key] = t; return acc; },
  {},
);

function ymd(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${dd}`;
}

function startOfMonth(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), 1);
}

function endOfMonth(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth() + 1, 0);
}

function fmtDate(iso: string): string {
  const d = new Date(iso + 'T00:00:00');
  return d.toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' });
}

export default function Calendar() {
  const [cursor, setCursor] = useState(() => startOfMonth(new Date()));
  const [activeTraditions, setActiveTraditions] = useState<Set<SpiritualTradition>>(
    () => new Set(TRADITIONS.map((t) => t.key)),
  );
  const [selected, setSelected] = useState<SpiritualEvent | null>(null);
  const [creating, setCreating] = useState(false);

  const from = ymd(startOfMonth(cursor));
  const to = ymd(endOfMonth(cursor));
  const traditionsParam = Array.from(activeTraditions).join(',');

  const { data: rangeData, isLoading } = useQuery({
    queryKey: ['calendar', from, to, traditionsParam],
    queryFn: () => calendarApi.range({
      from, to,
      traditions: traditionsParam || undefined,
    }),
  });

  const { data: today } = useQuery({
    queryKey: ['calendar-today'],
    queryFn: () => calendarApi.today(),
  });

  const events = rangeData?.events ?? [];
  const eventsByDate = useMemo(() => {
    const map: Record<string, SpiritualEvent[]> = {};
    for (const ev of events) {
      (map[ev.date] ||= []).push(ev);
    }
    return map;
  }, [events]);

  return (
    <div className="p-10 max-w-7xl mx-auto space-y-8">
      <header className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-2xl bg-accent-amethyst/10 flex items-center justify-center">
              <CalendarDays className="w-5 h-5 text-accent-amethyst" />
            </div>
            <h1 className="text-3xl font-black tracking-tight">Calendário Espiritual</h1>
          </div>
          <p className="text-secondary text-sm font-medium">
            Datas que pesam: orixás, equinócios, lua, festas. Use para criar campanhas.
          </p>
        </div>
        <button
          onClick={() => setCreating(true)}
          className="px-4 py-2.5 bg-bg-surface border border-border hover:border-accent-amethyst/30 rounded-xl text-xs font-bold flex items-center gap-2"
        >
          <Plus className="w-3.5 h-3.5" />
          Adicionar data custom
        </button>
      </header>

      <div className="bg-bg-surface border border-border rounded-3xl p-5">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-[10px] font-black uppercase tracking-widest text-secondary mr-2">
            Tradições:
          </span>
          {TRADITIONS.map((t) => (
            <button
              key={t.key}
              onClick={() => {
                const next = new Set(activeTraditions);
                if (next.has(t.key)) next.delete(t.key); else next.add(t.key);
                setActiveTraditions(next);
              }}
              className={`text-[11px] px-3 py-1.5 rounded-lg border transition-all flex items-center gap-1.5 font-bold ${
                activeTraditions.has(t.key)
                  ? 'bg-accent-amethyst text-white border-accent-amethyst'
                  : 'bg-bg-primary border-border text-secondary'
              }`}
            >
              <span>{t.emoji}</span>
              {t.label}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-6">
        <MonthView
          cursor={cursor}
          onCursor={setCursor}
          eventsByDate={eventsByDate}
          loading={isLoading}
          onPick={setSelected}
        />

        <UpcomingPanel today={today?.events ?? []} onPick={setSelected} />
      </div>

      {selected && (
        <DateDetailModal
          event={selected}
          onClose={() => setSelected(null)}
        />
      )}

      {creating && (
        <CreateCustomDateModal onClose={() => setCreating(false)} />
      )}
    </div>
  );
}

function MonthView({
  cursor, onCursor, eventsByDate, loading, onPick,
}: {
  cursor: Date;
  onCursor: (d: Date) => void;
  eventsByDate: Record<string, SpiritualEvent[]>;
  loading: boolean;
  onPick: (e: SpiritualEvent) => void;
}) {
  const monthLabel = cursor.toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' });

  // Layout: pad to start at Sunday=0
  const first = startOfMonth(cursor);
  const last = endOfMonth(cursor);
  const padBefore = first.getDay();
  const totalDays = last.getDate();
  const cells: Array<{ key: string; date?: Date; iso?: string }> = [];
  for (let i = 0; i < padBefore; i++) cells.push({ key: `pad-${i}` });
  for (let i = 1; i <= totalDays; i++) {
    const d = new Date(cursor.getFullYear(), cursor.getMonth(), i);
    cells.push({ key: ymd(d), date: d, iso: ymd(d) });
  }
  while (cells.length % 7 !== 0) cells.push({ key: `pad-end-${cells.length}` });

  const todayIso = ymd(new Date());

  return (
    <div className="bg-bg-surface border border-border rounded-3xl p-5">
      <div className="flex items-center justify-between mb-4">
        <button
          onClick={() => onCursor(new Date(cursor.getFullYear(), cursor.getMonth() - 1, 1))}
          className="p-2 rounded-lg bg-bg-primary border border-border hover:border-accent-amethyst/30"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>
        <h2 className="text-lg font-black tracking-tight capitalize">{monthLabel}</h2>
        <button
          onClick={() => onCursor(new Date(cursor.getFullYear(), cursor.getMonth() + 1, 1))}
          className="p-2 rounded-lg bg-bg-primary border border-border hover:border-accent-amethyst/30"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>

      <div className="grid grid-cols-7 gap-1.5 text-[9px] font-black uppercase tracking-widest text-secondary mb-2">
        {['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'].map((d) => (
          <div key={d} className="text-center">{d}</div>
        ))}
      </div>

      {loading ? (
        <div className="grid grid-cols-7 gap-1.5">
          {Array.from({ length: 35 }).map((_, i) => (
            <div key={i} className="aspect-square bg-bg-primary rounded-lg animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-7 gap-1.5">
          {cells.map((c) => {
            if (!c.date) {
              return <div key={c.key} className="aspect-square" />;
            }
            const evs = eventsByDate[c.iso!] || [];
            const isToday = c.iso === todayIso;
            return (
              <button
                key={c.key}
                onClick={() => evs.length && onPick(evs[0])}
                disabled={evs.length === 0}
                className={`aspect-square rounded-lg border p-1.5 text-left transition-all flex flex-col ${
                  evs.length
                    ? 'bg-bg-primary border-border hover:border-accent-amethyst/40 cursor-pointer'
                    : 'bg-bg-primary/30 border-transparent cursor-default'
                } ${isToday ? 'ring-2 ring-accent-amethyst' : ''}`}
              >
                <div className={`text-xs font-black tabular-nums ${isToday ? 'text-accent-amethyst' : 'text-primary'}`}>
                  {c.date.getDate()}
                </div>
                <div className="flex flex-wrap gap-0.5 mt-1 flex-1 overflow-hidden">
                  {evs.slice(0, 3).map((ev, i) => {
                    const meta = TRADITION_META[ev.tradition];
                    return (
                      <span
                        key={i}
                        title={ev.name}
                        className="text-[9px]"
                      >
                        {meta?.emoji || '✦'}
                      </span>
                    );
                  })}
                  {evs.length > 3 && (
                    <span className="text-[9px] text-secondary">+{evs.length - 3}</span>
                  )}
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

function UpcomingPanel({
  today, onPick,
}: {
  today: SpiritualEvent[];
  onPick: (e: SpiritualEvent) => void;
}) {
  const todayEvents = today.filter((e) => e.days_from_today === 0);
  const upcoming = today.filter((e) => (e.days_from_today ?? 0) > 0).slice(0, 12);

  return (
    <div className="space-y-4 self-start sticky top-6">
      <section className="bg-bg-surface border border-border rounded-3xl p-5">
        <h2 className="text-[10px] font-black uppercase tracking-widest text-secondary mb-3 flex items-center gap-1.5">
          <Sparkles className="w-3 h-3 text-accent-amethyst" />
          Hoje
        </h2>
        {todayEvents.length === 0 ? (
          <p className="text-xs text-secondary">Sem datas marcadas hoje além da lua.</p>
        ) : (
          <div className="space-y-2">
            {todayEvents.map((ev, i) => <EventRow key={i} event={ev} onPick={onPick} />)}
          </div>
        )}
      </section>

      <section className="bg-bg-surface border border-border rounded-3xl p-5">
        <h2 className="text-[10px] font-black uppercase tracking-widest text-secondary mb-3 flex items-center gap-1.5">
          <CalendarDays className="w-3 h-3 text-accent-amethyst" />
          Próximas
        </h2>
        {upcoming.length === 0 ? (
          <p className="text-xs text-secondary">Sem datas previstas nos próximos 14 dias.</p>
        ) : (
          <div className="space-y-2">
            {upcoming.map((ev, i) => <EventRow key={i} event={ev} onPick={onPick} />)}
          </div>
        )}
      </section>
    </div>
  );
}

function EventRow({
  event, onPick,
}: {
  event: SpiritualEvent;
  onPick: (e: SpiritualEvent) => void;
}) {
  const meta = TRADITION_META[event.tradition];
  return (
    <button
      onClick={() => onPick(event)}
      className={`w-full text-left bg-bg-primary border ${meta?.color || 'border-border'} rounded-xl p-2.5 hover:bg-bg-surface transition-all`}
    >
      <div className="flex items-center justify-between gap-2 mb-0.5">
        <div className="text-xs font-black truncate flex items-center gap-1">
          <span>{meta?.emoji || '✦'}</span>
          {event.name}
        </div>
        <div className="text-[10px] text-secondary font-bold tabular-nums flex-shrink-0">
          {event.days_from_today === 0 ? 'hoje' :
           event.days_from_today === 1 ? 'amanhã' :
           event.days_from_today != null ? `+${event.days_from_today}d` : fmtDate(event.date)}
        </div>
      </div>
      {event.description && (
        <p className="text-[10px] text-secondary line-clamp-2 leading-relaxed">
          {event.description}
        </p>
      )}
    </button>
  );
}

function DateDetailModal({
  event, onClose,
}: {
  event: SpiritualEvent;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const [copied, setCopied] = useState<number | null>(null);

  const suggestMut = useMutation({
    mutationFn: () => {
      if (!event.id) throw new Error('event_has_no_id');
      return calendarApi.suggestMessage(event.id);
    },
    onError: handleApiError('Erro ao gerar sugestões'),
  });

  const deleteMut = useMutation({
    mutationFn: () => {
      if (!event.id) throw new Error('event_has_no_id');
      return calendarApi.removeCustom(event.id);
    },
    onSuccess: () => {
      toast.success('Removida');
      qc.invalidateQueries({ queryKey: ['calendar'] });
      qc.invalidateQueries({ queryKey: ['calendar-today'] });
      onClose();
    },
    onError: handleApiError('Erro ao remover'),
  });

  const copyMessage = (i: number, text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(i);
    setTimeout(() => setCopied(null), 1800);
  };

  const meta = TRADITION_META[event.tradition];
  const messages = suggestMut.data?.suggestion?.messages ?? [];

  return (
    <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-6">
      <div className="bg-bg-surface border border-border rounded-3xl max-w-xl w-full max-h-[85vh] overflow-hidden flex flex-col">
        <div className="p-5 border-b border-border flex items-start justify-between gap-3">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-2xl">{meta?.emoji || '✦'}</span>
              <h2 className="text-xl font-black tracking-tight">{event.name}</h2>
            </div>
            <div className="text-[10px] uppercase font-black tracking-widest text-secondary flex items-center gap-2 mt-1">
              {meta?.label || event.tradition}
              <span>·</span>
              <span>{fmtDate(event.date)}</span>
            </div>
          </div>
          <button onClick={onClose} className="text-secondary hover:text-primary">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-5 overflow-y-auto space-y-4">
          {event.description && (
            <p className="text-sm leading-relaxed text-primary">{event.description}</p>
          )}

          {event.lunar && (
            <div className="bg-bg-primary border border-indigo-400/30 rounded-xl p-3 text-xs flex items-center gap-2">
              <Moon className="w-4 h-4 text-indigo-300" />
              Fase {event.lunar.phase_name} · {event.lunar.illumination_pct}% iluminada
            </div>
          )}

          {event.id && (
            <div className="border-t border-border pt-4">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-[10px] font-black uppercase tracking-widest text-secondary flex items-center gap-1.5">
                  <Wand2 className="w-3 h-3" />
                  Mensagens IA pra enviar
                </h3>
                <button
                  onClick={() => suggestMut.mutate()}
                  disabled={suggestMut.isPending}
                  className="text-[11px] text-accent-amethyst hover:underline flex items-center gap-1 font-bold"
                >
                  <RefreshCw className={`w-3 h-3 ${suggestMut.isPending ? 'animate-spin' : ''}`} />
                  {messages.length ? 'Regen' : 'Gerar'}
                </button>
              </div>
              {messages.length === 0 && !suggestMut.isPending && (
                <p className="text-[11px] text-secondary">
                  Clique "Gerar" para a IA criar 3 mensagens de WhatsApp baseadas nesta data.
                </p>
              )}
              {suggestMut.isPending && (
                <p className="text-[11px] text-secondary text-center py-3">Gerando sugestões…</p>
              )}
              <div className="space-y-2">
                {messages.map((m, i) => (
                  <div key={i} className="bg-bg-primary border border-border rounded-xl p-3">
                    <p className="text-[12px] leading-relaxed mb-2">{m}</p>
                    <button
                      onClick={() => copyMessage(i, m)}
                      className="text-[10px] text-accent-amethyst hover:underline flex items-center gap-1 font-bold"
                    >
                      {copied === i ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                      {copied === i ? 'Copiado' : 'Copiar'}
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {event.is_custom && (
          <div className="p-4 border-t border-border">
            <button
              onClick={() => {
                if (confirm(`Remover "${event.name}"?`)) deleteMut.mutate();
              }}
              disabled={deleteMut.isPending}
              className="text-[11px] text-rose-400 hover:underline flex items-center gap-1 font-bold"
            >
              <Trash2 className="w-3 h-3" />
              Remover data custom
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function CreateCustomDateModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const [name, setName] = useState('');
  const [tradition, setTradition] = useState<SpiritualTradition>('secular');
  const [month, setMonth] = useState<string>('');
  const [day, setDay] = useState<string>('');
  const [description, setDescription] = useState('');

  const createMut = useMutation({
    mutationFn: () => calendarApi.createCustom({
      name: name.trim(),
      tradition,
      month: month ? Number(month) : undefined,
      day: day ? Number(day) : undefined,
      description: description.trim() || undefined,
    }),
    onSuccess: () => {
      toast.success('Data criada');
      qc.invalidateQueries({ queryKey: ['calendar'] });
      qc.invalidateQueries({ queryKey: ['calendar-today'] });
      onClose();
    },
    onError: handleApiError('Erro ao criar'),
  });

  const valid =
    name.trim().length >= 3 &&
    month && day &&
    Number(month) >= 1 && Number(month) <= 12 &&
    Number(day) >= 1 && Number(day) <= 31;

  return (
    <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-6">
      <div className="bg-bg-surface border border-border rounded-3xl max-w-md w-full overflow-hidden">
        <div className="p-5 border-b border-border flex items-start justify-between">
          <h2 className="text-lg font-black tracking-tight">Nova data espiritual</h2>
          <button onClick={onClose} className="text-secondary hover:text-primary">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-5 space-y-3">
          <Field label="Nome">
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={200}
              placeholder="Ex.: Aniversário do tarô"
              className="w-full bg-bg-primary border border-border rounded-xl px-3 py-2 text-xs"
            />
          </Field>

          <Field label="Tradição">
            <select
              value={tradition}
              onChange={(e) => setTradition(e.target.value as SpiritualTradition)}
              className="w-full bg-bg-primary border border-border rounded-xl px-3 py-2 text-xs"
            >
              {TRADITIONS.map((t) => (
                <option key={t.key} value={t.key}>{t.emoji} {t.label}</option>
              ))}
            </select>
          </Field>

          <div className="grid grid-cols-2 gap-3">
            <Field label="Mês (1-12)">
              <input
                type="number"
                min={1} max={12}
                value={month}
                onChange={(e) => setMonth(e.target.value.replace(/[^0-9]/g, ''))}
                className="w-full bg-bg-primary border border-border rounded-xl px-3 py-2 text-xs"
              />
            </Field>
            <Field label="Dia (1-31)">
              <input
                type="number"
                min={1} max={31}
                value={day}
                onChange={(e) => setDay(e.target.value.replace(/[^0-9]/g, ''))}
                className="w-full bg-bg-primary border border-border rounded-xl px-3 py-2 text-xs"
              />
            </Field>
          </div>

          <Field label="Descrição (opcional)">
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              className="w-full bg-bg-primary border border-border rounded-xl px-3 py-2 text-xs resize-none"
            />
          </Field>
        </div>

        <div className="p-4 border-t border-border flex gap-2">
          <button
            onClick={onClose}
            className="flex-1 px-3 py-2 bg-bg-primary border border-border rounded-xl text-[11px] font-bold"
          >
            Cancelar
          </button>
          <button
            onClick={() => createMut.mutate()}
            disabled={!valid || createMut.isPending}
            className="flex-1 px-3 py-2 bg-accent-amethyst hover:bg-accent-amethyst/90 disabled:opacity-30 text-white rounded-xl text-[11px] font-black uppercase tracking-widest flex items-center justify-center gap-1.5"
          >
            <Plus className="w-3 h-3" />
            {createMut.isPending ? 'Criando…' : 'Criar'}
          </button>
        </div>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="text-[9px] font-black uppercase tracking-widest text-secondary block mb-1">
        {label}
      </label>
      {children}
    </div>
  );
}
