import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { CalendarDays, Plus, Users, MapPin, Clock, DollarSign, Ticket } from 'lucide-react';
import { eventsApi, type Event } from '../api/saas';
import { handleApiError } from '../lib/handleApiError';
import { toast } from '../lib/toast';

export default function Events() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [selected, setSelected] = useState<number | null>(null);

  const { data, isLoading } = useQuery({ queryKey: ['events-list'], queryFn: eventsApi.list });
  const items = data?.events ?? [];

  return (
    <div className="p-10 max-w-6xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-2xl bg-accent-amethyst/10 flex items-center justify-center">
              <CalendarDays className="w-5 h-5 text-accent-amethyst" />
            </div>
            <h1 className="text-3xl font-black tracking-tight">Eventos & Retiros</h1>
          </div>
          <p className="text-secondary text-sm font-medium">Crie e gerencie eventos presenciais e online — workshops, retiros e cerimônias.</p>
        </div>
        <button onClick={() => setShowCreate(true)} className="flex items-center gap-2 px-5 py-3 bg-accent-amethyst hover:bg-accent-amethyst/90 text-white rounded-2xl font-black uppercase tracking-widest text-xs transition-all">
          <Plus className="w-4 h-4" /> Novo Evento
        </button>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 animate-pulse">{[1,2].map(i => <div key={i} className="h-48 bg-bg-surface rounded-2xl" />)}</div>
      ) : items.length === 0 ? (
        <div className="bg-bg-surface border border-dashed border-border rounded-3xl p-12 text-center">
          <CalendarDays className="w-12 h-12 mx-auto text-secondary/40 mb-4" />
          <h3 className="font-black text-lg mb-2">Nenhum evento ainda</h3>
          <p className="text-secondary text-sm mb-4">Crie seu primeiro retiro espiritual, workshop ou cerimônia.</p>
          <button onClick={() => setShowCreate(true)} className="px-5 py-3 bg-accent-amethyst text-white rounded-2xl text-xs font-black uppercase tracking-widest">Criar Evento</button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {items.map(ev => (
            <button key={ev.id} onClick={() => setSelected(ev.id)} className="text-left bg-bg-surface border border-border hover:border-accent-amethyst/30 rounded-2xl p-6 transition-all group">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h3 className="font-black text-lg group-hover:text-accent-amethyst transition-colors">{ev.title}</h3>
                  <span className="text-[9px] font-black uppercase tracking-widest text-secondary">{ev.event_type}</span>
                </div>
                <span className={`text-[9px] font-black uppercase tracking-widest px-2.5 py-1 rounded-lg border ${
                  ev.status === 'published' ? 'text-emerald-500 bg-emerald-500/10 border-emerald-500/30'
                  : ev.status === 'draft' ? 'text-amber-400 bg-amber-500/10 border-amber-500/30'
                  : 'text-zinc-400 bg-zinc-500/10 border-zinc-500/30'
                }`}>{ev.status}</span>
              </div>
              <div className="flex flex-wrap gap-3 text-[11px] text-secondary mb-3">
                <span className="flex items-center gap-1"><Clock className="w-3 h-3" />{new Date(ev.start_date).toLocaleDateString('pt-BR')}</span>
                {ev.location && <span className="flex items-center gap-1"><MapPin className="w-3 h-3" />{ev.location}</span>}
                <span className="flex items-center gap-1"><Users className="w-3 h-3" />{ev.total_registered}/{ev.max_attendees || '∞'}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xl font-black font-mono tracking-tight">R${(ev.price_cents / 100).toFixed(2)}</span>
                {ev.early_bird_price_cents && <span className="text-[10px] text-emerald-500 font-bold">Early bird: R${(ev.early_bird_price_cents / 100).toFixed(2)}</span>}
              </div>
            </button>
          ))}
        </div>
      )}

      {showCreate && <CreateEventModal onClose={() => setShowCreate(false)} onCreated={() => { setShowCreate(false); qc.invalidateQueries({ queryKey: ['events-list'] }); }} />}
      {selected && <EventDetailModal eventId={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}

function CreateEventModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [form, setForm] = useState({ title: '', description: '', event_type: 'workshop', max_attendees: 20, price_cents: 29900, location: '', start_date: '', end_date: '' });
  const set = (k: string, v: unknown) => setForm(f => ({ ...f, [k]: v }));

  const createMut = useMutation({
    mutationFn: () => eventsApi.create(form),
    onSuccess: () => { toast.success('Evento criado!'); onCreated(); },
    onError: handleApiError('Erro ao criar evento'),
  });

  return (
    <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-6">
      <div className="bg-bg-surface border border-border rounded-3xl p-8 max-w-lg w-full space-y-4 max-h-[90vh] overflow-y-auto">
        <h2 className="text-xl font-black tracking-tight">Novo Evento</h2>
        <F label="Título"><input value={form.title} onChange={e => set('title', e.target.value)} placeholder="Retiro de Autoconhecimento" className="inp" /></F>
        <F label="Tipo">
          <div className="flex gap-2">{['workshop', 'retreat', 'ceremony', 'webinar', 'course'].map(t => (
            <button key={t} onClick={() => set('event_type', t)} className={`flex-1 px-2 py-2 rounded-xl text-[10px] font-bold ${form.event_type === t ? 'bg-accent-amethyst text-white' : 'bg-bg-primary text-secondary'}`}>{t}</button>
          ))}</div>
        </F>
        <F label="Descrição"><textarea value={form.description} onChange={e => set('description', e.target.value)} rows={3} className="inp resize-none" /></F>
        <div className="grid grid-cols-2 gap-3">
          <F label="Início"><input type="datetime-local" value={form.start_date} onChange={e => set('start_date', e.target.value)} className="inp" /></F>
          <F label="Fim"><input type="datetime-local" value={form.end_date} onChange={e => set('end_date', e.target.value)} className="inp" /></F>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <F label="Vagas"><input type="number" value={form.max_attendees} onChange={e => set('max_attendees', +e.target.value)} className="inp" /></F>
          <F label="Preço (R$)"><input type="number" value={form.price_cents / 100} onChange={e => set('price_cents', Math.round(+e.target.value * 100))} step={0.01} className="inp" /></F>
        </div>
        <F label="Local"><input value={form.location} onChange={e => set('location', e.target.value)} placeholder="São Paulo, SP ou Online" className="inp" /></F>
        <div className="flex gap-3 pt-2">
          <button onClick={onClose} className="flex-1 px-5 py-3 bg-bg-primary border border-border rounded-2xl text-sm font-bold">Cancelar</button>
          <button onClick={() => createMut.mutate()} disabled={!form.title || !form.start_date || createMut.isPending} className="flex-1 px-5 py-3 bg-accent-amethyst hover:bg-accent-amethyst/90 disabled:opacity-30 text-white rounded-2xl text-sm font-black uppercase tracking-widest">
            {createMut.isPending ? 'Criando...' : 'Criar Evento'}
          </button>
        </div>
      </div>
    </div>
  );
}

function EventDetailModal({ eventId, onClose }: { eventId: number; onClose: () => void }) {
  const { data } = useQuery({ queryKey: ['event-detail', eventId], queryFn: () => eventsApi.get(eventId) });
  const { data: regsData } = useQuery({ queryKey: ['event-regs', eventId], queryFn: () => eventsApi.registrations(eventId) });
  const regs = regsData?.registrations ?? [];

  return (
    <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-6">
      <div className="bg-bg-surface border border-border rounded-3xl p-8 max-w-lg w-full space-y-5 max-h-[90vh] overflow-y-auto">
        <div className="flex justify-between items-start">
          <h2 className="text-xl font-black">{data?.title || 'Carregando...'}</h2>
          <button onClick={onClose} className="text-secondary hover:text-primary">✕</button>
        </div>
        {data && (
          <>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="bg-bg-primary rounded-xl p-3"><div className="text-[10px] text-secondary font-black uppercase mb-1">Inscritos</div><div className="font-black text-lg">{data.total_registered}</div></div>
              <div className="bg-bg-primary rounded-xl p-3"><div className="text-[10px] text-secondary font-black uppercase mb-1">Receita</div><div className="font-black text-lg font-mono">R${((data.total_registered * data.price_cents) / 100).toFixed(0)}</div></div>
            </div>
            <h3 className="text-sm font-black">Inscritos ({regs.length})</h3>
            {regs.length === 0 ? <p className="text-secondary text-sm">Nenhum inscrito ainda.</p> : (
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {regs.map(r => (
                  <div key={r.id} className="flex items-center justify-between bg-bg-primary rounded-xl px-4 py-2.5 text-sm">
                    <span className="font-bold">{r.name}</span>
                    <span className="text-[10px] text-secondary">{r.phone}</span>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function F({ label, children }: { label: string; children: React.ReactNode }) {
  return <div><label className="text-[10px] uppercase font-black tracking-widest text-secondary mb-1.5 block">{label}</label>{children}</div>;
}
