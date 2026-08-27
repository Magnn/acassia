import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  CalendarClock, Plus, Clock, CheckCircle2, XCircle, User, Phone,
  ChevronRight, AlertCircle, Calendar,
} from 'lucide-react';
import { schedulingApi, type Appointment, type Slot } from '../api/saas';
import { handleApiError } from '../lib/handleApiError';
import { toast } from '../lib/toast';

const TABS = ['agenda', 'slots', 'consultas'] as const;
type Tab = typeof TABS[number];

export default function Scheduling() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<Tab>('agenda');
  const [showCreate, setShowCreate] = useState(false);
  const [filter, setFilter] = useState('');

  const { data: todayData, isLoading: todayLoading } = useQuery({
    queryKey: ['scheduling-today'],
    queryFn: schedulingApi.today,
    refetchInterval: 30000,
  });
  const { data: slotsData } = useQuery({
    queryKey: ['scheduling-slots'],
    queryFn: () => schedulingApi.slots(),
  });
  const { data: apptData } = useQuery({
    queryKey: ['scheduling-appointments', filter],
    queryFn: () => schedulingApi.appointments(filter ? { status: filter } : undefined),
  });

  const todayAppts = todayData?.appointments ?? [];
  const allSlots = slotsData?.slots ?? [];
  const allAppts = apptData?.appointments ?? [];
  const freeSlots = allSlots.filter(s => !s.is_booked && !s.is_blocked);

  return (
    <div className="p-10 max-w-6xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-2xl bg-accent-amethyst/10 flex items-center justify-center">
              <CalendarClock className="w-5 h-5 text-accent-amethyst" />
            </div>
            <h1 className="text-3xl font-black tracking-tight">Agendamento</h1>
          </div>
          <p className="text-secondary text-sm font-medium">
            Gerencie seus horários, consultas e disponibilidade para clientes.
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-5 py-3 bg-accent-amethyst hover:bg-accent-amethyst/90 text-white rounded-2xl font-black uppercase tracking-widest text-xs transition-all"
        >
          <Plus className="w-4 h-4" />
          Novo Horário
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Hoje', value: todayAppts.length, icon: Calendar, color: 'text-accent-amethyst' },
          { label: 'Slots Livres', value: freeSlots.length, icon: Clock, color: 'text-emerald-500' },
          { label: 'Confirmadas', value: allAppts.filter(a => a.status === 'confirmed').length, icon: CheckCircle2, color: 'text-blue-500' },
          { label: 'Pendentes', value: allAppts.filter(a => a.status === 'pending').length, icon: AlertCircle, color: 'text-amber-400' },
        ].map(s => (
          <div key={s.label} className="bg-bg-surface border border-border rounded-2xl p-5">
            <div className="flex items-center gap-2 mb-2">
              <s.icon className={`w-4 h-4 ${s.color}`} />
              <span className="text-[10px] font-black uppercase tracking-widest text-secondary">{s.label}</span>
            </div>
            <div className="text-3xl font-black tracking-tight">{s.value}</div>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-bg-surface border border-border rounded-2xl p-1.5 w-fit">
        {TABS.map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-5 py-2.5 rounded-xl text-xs font-black uppercase tracking-widest transition-all ${
              tab === t ? 'bg-accent-amethyst text-white shadow-lg' : 'text-secondary hover:text-primary'
            }`}
          >
            {t === 'agenda' ? '📅 Hoje' : t === 'slots' ? '🕐 Horários' : '📋 Consultas'}
          </button>
        ))}
      </div>

      {/* Content */}
      {tab === 'agenda' && (
        <div className="space-y-3">
          {todayLoading ? (
            <div className="animate-pulse space-y-3">
              {[1,2,3].map(i => <div key={i} className="h-20 bg-bg-surface rounded-2xl" />)}
            </div>
          ) : todayAppts.length === 0 ? (
            <EmptyState icon={Calendar} title="Agenda livre hoje" subtitle="Nenhuma consulta marcada para hoje." />
          ) : (
            todayAppts.map(a => <AppointmentCard key={a.id} appt={a} onRefresh={() => qc.invalidateQueries({ queryKey: ['scheduling-today'] })} />)
          )}
        </div>
      )}

      {tab === 'slots' && (
        <div className="space-y-3">
          {allSlots.length === 0 ? (
            <EmptyState icon={Clock} title="Nenhum horário cadastrado" subtitle="Crie seus horários de atendimento." cta="Criar Horários" onCta={() => setShowCreate(true)} />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {allSlots.map(s => (
                <div key={s.id} className={`bg-bg-surface border rounded-2xl p-4 transition-all ${s.is_booked ? 'border-amber-500/30 bg-amber-500/5' : s.is_blocked ? 'border-red-500/30 opacity-50' : 'border-border hover:border-accent-amethyst/30'}`}>
                  <div className="flex items-center justify-between mb-2">
                    <div className="text-lg font-black tracking-tight">
                      {s.slot_time ? new Date(s.slot_time).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }) : '—'}
                    </div>
                    <span className={`text-[9px] font-black uppercase tracking-widest px-2 py-0.5 rounded-md ${
                      s.is_booked ? 'bg-amber-500/10 text-amber-400' : s.is_blocked ? 'bg-red-500/10 text-red-400' : 'bg-emerald-500/10 text-emerald-500'
                    }`}>
                      {s.is_booked ? 'Reservado' : s.is_blocked ? 'Bloqueado' : 'Livre'}
                    </span>
                  </div>
                  <div className="text-[11px] text-secondary">
                    {s.slot_date || '—'} • {s.duration_minutes}min
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {tab === 'consultas' && (
        <div className="space-y-4">
          <div className="flex gap-2">
            {['', 'pending', 'confirmed', 'completed', 'cancelled'].map(f => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-3 py-1.5 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all ${
                  filter === f ? 'bg-accent-amethyst text-white' : 'bg-bg-surface text-secondary hover:text-primary'
                }`}
              >
                {f || 'Todas'}
              </button>
            ))}
          </div>
          {allAppts.length === 0 ? (
            <EmptyState icon={CalendarClock} title="Nenhuma consulta" subtitle="As consultas aparecerão quando clientes agendarem." />
          ) : (
            allAppts.map(a => <AppointmentCard key={a.id} appt={a} onRefresh={() => qc.invalidateQueries({ queryKey: ['scheduling-appointments'] })} />)
          )}
        </div>
      )}

      {/* Create Modal */}
      {showCreate && (
        <CreateSlotModal
          onClose={() => setShowCreate(false)}
          onCreated={() => {
            setShowCreate(false);
            qc.invalidateQueries({ queryKey: ['scheduling-slots'] });
            toast.success('Horários criados!');
          }}
        />
      )}
    </div>
  );
}

function AppointmentCard({ appt: a, onRefresh }: { appt: Appointment; onRefresh: () => void }) {
  const updateMut = useMutation({
    mutationFn: (status: string) => schedulingApi.updateAppointment(a.id, { status }),
    onSuccess: () => { toast.success('Status atualizado'); onRefresh(); },
    onError: handleApiError('Erro ao atualizar'),
  });

  const statusConfig: Record<string, { color: string; label: string }> = {
    pending: { color: 'text-amber-400 bg-amber-500/10 border-amber-500/30', label: 'Pendente' },
    confirmed: { color: 'text-blue-400 bg-blue-500/10 border-blue-500/30', label: 'Confirmada' },
    completed: { color: 'text-emerald-500 bg-emerald-500/10 border-emerald-500/30', label: 'Concluída' },
    cancelled: { color: 'text-red-400 bg-red-500/10 border-red-500/30', label: 'Cancelada' },
    no_show: { color: 'text-zinc-400 bg-zinc-500/10 border-zinc-500/30', label: 'Não compareceu' },
  };
  const cfg = statusConfig[a.status] || statusConfig.pending;

  return (
    <div className="bg-bg-surface border border-border hover:border-accent-amethyst/20 rounded-2xl p-5 transition-all">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-accent-amethyst/10 flex items-center justify-center text-xs font-black text-accent-amethyst">
            {(a.client_name || '??').substring(0, 2).toUpperCase()}
          </div>
          <div>
            <div className="font-black text-sm">{a.client_name}</div>
            <div className="text-[11px] text-secondary flex items-center gap-1">
              <Phone className="w-3 h-3" /> {a.client_phone}
            </div>
          </div>
        </div>
        <span className={`text-[9px] font-black uppercase tracking-widest px-2.5 py-1 rounded-lg border ${cfg.color}`}>
          {cfg.label}
        </span>
      </div>
      <div className="flex items-center gap-4 text-[11px] text-secondary mb-3">
        <span className="flex items-center gap-1">
          <Calendar className="w-3 h-3" />
          {new Date(a.scheduled_at).toLocaleDateString('pt-BR')}
        </span>
        <span className="flex items-center gap-1">
          <Clock className="w-3 h-3" />
          {new Date(a.scheduled_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
        </span>
        <span>{a.duration_minutes}min • {a.modality}</span>
      </div>
      {a.notes_before && (
        <div className="text-[11px] text-secondary bg-bg-primary rounded-xl p-3 mb-3">"{a.notes_before}"</div>
      )}
      {(a.status === 'pending' || a.status === 'confirmed') && (
        <div className="flex gap-2">
          {a.status === 'pending' && (
            <button onClick={() => updateMut.mutate('confirmed')} className="flex-1 px-3 py-2 bg-blue-500/10 text-blue-400 hover:bg-blue-500/20 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all">
              Confirmar
            </button>
          )}
          {a.status === 'confirmed' && (
            <button onClick={() => updateMut.mutate('completed')} className="flex-1 px-3 py-2 bg-emerald-500/10 text-emerald-500 hover:bg-emerald-500/20 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all">
              <CheckCircle2 className="w-3 h-3 inline mr-1" /> Concluir
            </button>
          )}
          <button onClick={() => updateMut.mutate('cancelled')} className="px-3 py-2 bg-red-500/10 text-red-400 hover:bg-red-500/20 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all">
            <XCircle className="w-3 h-3 inline mr-1" /> Cancelar
          </button>
        </div>
      )}
    </div>
  );
}

function CreateSlotModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
  const [startTime, setStartTime] = useState('09:00');
  const [endTime, setEndTime] = useState('18:00');
  const [duration, setDuration] = useState(60);
  const [mode, setMode] = useState<'single' | 'week'>('single');

  const createMut = useMutation({
    mutationFn: () => {
      if (mode === 'week') {
        const dates: string[] = [];
        const d = new Date(date + 'T12:00:00');
        for (let i = 0; i < 7; i++) {
          const day = d.getDay();
          if (day >= 1 && day <= 5) dates.push(d.toISOString().split('T')[0]);
          d.setDate(d.getDate() + 1);
        }
        return schedulingApi.bulkSlots({ dates, start_time: startTime, end_time: endTime, duration_minutes: duration })
          .then((res) => ({ ...res, ids: [] as number[] }));
      }
      return schedulingApi.createSlot({ date, start_time: startTime, end_time: endTime, duration_minutes: duration });
    },
    onSuccess: onCreated,
    onError: handleApiError('Erro ao criar horários'),
  });

  return (
    <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-6">
      <div className="bg-bg-surface border border-border rounded-3xl p-8 max-w-md w-full space-y-5">
        <h2 className="text-xl font-black tracking-tight">Novo Horário</h2>

        <div className="flex gap-2">
          {(['single', 'week'] as const).map(m => (
            <button key={m} onClick={() => setMode(m)} className={`flex-1 px-3 py-2.5 rounded-xl text-xs font-bold transition-all ${mode === m ? 'bg-accent-amethyst text-white' : 'bg-bg-primary text-secondary'}`}>
              {m === 'single' ? '📅 Dia único' : '📆 Semana inteira'}
            </button>
          ))}
        </div>

        <Field label="Data inicial">
          <input type="date" value={date} onChange={e => setDate(e.target.value)} className="w-full bg-bg-primary border border-border rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-accent-amethyst/30" />
        </Field>

        <div className="grid grid-cols-2 gap-3">
          <Field label="Início">
            <input type="time" value={startTime} onChange={e => setStartTime(e.target.value)} className="w-full bg-bg-primary border border-border rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-accent-amethyst/30" />
          </Field>
          <Field label="Fim">
            <input type="time" value={endTime} onChange={e => setEndTime(e.target.value)} className="w-full bg-bg-primary border border-border rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-accent-amethyst/30" />
          </Field>
        </div>

        <Field label="Duração da sessão">
          <div className="flex gap-2">
            {[30, 45, 60, 90].map(m => (
              <button key={m} onClick={() => setDuration(m)} className={`flex-1 px-3 py-2 rounded-xl text-xs font-bold transition-all ${duration === m ? 'bg-accent-amethyst text-white' : 'bg-bg-primary text-secondary'}`}>
                {m}min
              </button>
            ))}
          </div>
        </Field>

        <div className="flex gap-3">
          <button onClick={onClose} className="flex-1 px-5 py-3 bg-bg-primary border border-border rounded-2xl text-sm font-bold">Cancelar</button>
          <button onClick={() => createMut.mutate()} disabled={createMut.isPending} className="flex-1 px-5 py-3 bg-accent-amethyst hover:bg-accent-amethyst/90 disabled:opacity-30 text-white rounded-2xl text-sm font-black uppercase tracking-widest transition-all">
            {createMut.isPending ? 'Criando...' : 'Criar'}
          </button>
        </div>
      </div>
    </div>
  );
}

function EmptyState({ icon: Icon, title, subtitle, cta, onCta }: { icon: typeof Calendar; title: string; subtitle: string; cta?: string; onCta?: () => void }) {
  return (
    <div className="bg-bg-surface border border-dashed border-border rounded-3xl p-12 text-center">
      <Icon className="w-12 h-12 mx-auto text-secondary/40 mb-4" />
      <h3 className="font-black text-lg mb-2">{title}</h3>
      <p className="text-secondary text-sm mb-4">{subtitle}</p>
      {cta && onCta && (
        <button onClick={onCta} className="px-5 py-3 bg-accent-amethyst hover:bg-accent-amethyst/90 text-white rounded-2xl text-xs font-black uppercase tracking-widest">{cta}</button>
      )}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="text-[10px] uppercase font-black tracking-widest text-secondary mb-1.5 block">{label}</label>
      {children}
    </div>
  );
}
