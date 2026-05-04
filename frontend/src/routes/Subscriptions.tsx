import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { RefreshCw, Plus, Pause, Play, Users, DollarSign, Calendar } from 'lucide-react';
import { subscriptionsApi, type Subscription } from '../api/saas';
import { handleApiError } from '../lib/handleApiError';
import { toast } from '../lib/toast';

export default function Subscriptions() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);

  const { data, isLoading } = useQuery({ queryKey: ['subscriptions-list'], queryFn: subscriptionsApi.list });
  const items = data?.subscriptions ?? [];
  const active = items.filter(s => s.status === 'active');
  const mrr = active.reduce((s, a) => s + a.price_cents, 0);

  return (
    <div className="p-10 max-w-5xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-2xl bg-accent-amethyst/10 flex items-center justify-center">
              <RefreshCw className="w-5 h-5 text-accent-amethyst" />
            </div>
            <h1 className="text-3xl font-black tracking-tight">Assinaturas & Pacotes</h1>
          </div>
          <p className="text-secondary text-sm font-medium">Receita recorrente — pacotes mensais com sessões incluídas.</p>
        </div>
        <button onClick={() => setShowCreate(true)} className="flex items-center gap-2 px-5 py-3 bg-accent-amethyst hover:bg-accent-amethyst/90 text-white rounded-2xl font-black uppercase tracking-widest text-xs transition-all">
          <Plus className="w-4 h-4" /> Novo Pacote
        </button>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {[
          { label: 'Ativas', value: active.length, icon: Users, color: 'text-emerald-500' },
          { label: 'MRR', value: `R$${(mrr / 100).toFixed(0)}`, icon: DollarSign, color: 'text-accent-amethyst' },
          { label: 'Total', value: items.length, icon: RefreshCw, color: 'text-blue-400' },
        ].map(s => (
          <div key={s.label} className="bg-bg-surface border border-border rounded-2xl p-5">
            <div className="flex items-center gap-2 mb-2">
              <s.icon className={`w-4 h-4 ${s.color}`} />
              <span className="text-[10px] font-black uppercase tracking-widest text-secondary">{s.label}</span>
            </div>
            <div className="text-2xl font-black tracking-tight">{s.value}</div>
          </div>
        ))}
      </div>

      {isLoading ? (
        <div className="space-y-3 animate-pulse">{[1,2,3].map(i => <div key={i} className="h-24 bg-bg-surface rounded-2xl" />)}</div>
      ) : items.length === 0 ? (
        <div className="bg-bg-surface border border-dashed border-border rounded-3xl p-12 text-center">
          <RefreshCw className="w-12 h-12 mx-auto text-secondary/40 mb-4" />
          <h3 className="font-black text-lg mb-2">Nenhuma assinatura</h3>
          <p className="text-secondary text-sm mb-4">Crie pacotes recorrentes — ex: "4 sessões/mês por R$800".</p>
          <button onClick={() => setShowCreate(true)} className="px-5 py-3 bg-accent-amethyst text-white rounded-2xl text-xs font-black uppercase tracking-widest">Criar Pacote</button>
        </div>
      ) : (
        <div className="space-y-3">{items.map(s => <SubCard key={s.id} sub={s} onRefresh={() => qc.invalidateQueries({ queryKey: ['subscriptions-list'] })} />)}</div>
      )}

      {showCreate && <CreateSubModal onClose={() => setShowCreate(false)} onCreated={() => { setShowCreate(false); qc.invalidateQueries({ queryKey: ['subscriptions-list'] }); }} />}
    </div>
  );
}

function SubCard({ sub: s, onRefresh }: { sub: Subscription; onRefresh: () => void }) {
  const pauseMut = useMutation({ mutationFn: () => subscriptionsApi.pause(s.id), onSuccess: () => { toast.success('Pausada'); onRefresh(); }, onError: handleApiError('Erro') });
  const resumeMut = useMutation({ mutationFn: () => subscriptionsApi.resume(s.id), onSuccess: () => { toast.success('Retomada'); onRefresh(); }, onError: handleApiError('Erro') });
  const renewMut = useMutation({ mutationFn: () => subscriptionsApi.renew(s.id), onSuccess: () => { toast.success('Renovada'); onRefresh(); }, onError: handleApiError('Erro') });

  const statusColors: Record<string, string> = {
    active: 'text-emerald-500 bg-emerald-500/10 border-emerald-500/30',
    paused: 'text-amber-400 bg-amber-500/10 border-amber-500/30',
    expired: 'text-zinc-400 bg-zinc-500/10 border-zinc-500/30',
    cancelled: 'text-red-400 bg-red-500/10 border-red-500/30',
  };

  return (
    <div className="bg-bg-surface border border-border hover:border-accent-amethyst/20 rounded-2xl p-5 transition-all">
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-black text-sm">{s.package_name}</h3>
          <p className="text-[11px] text-secondary">{s.lead_name || `Lead #${s.lead_id}`}</p>
        </div>
        <span className={`text-[9px] font-black uppercase tracking-widest px-2.5 py-1 rounded-lg border ${statusColors[s.status] || ''}`}>{s.status}</span>
      </div>
      <div className="flex items-center gap-4 text-[11px] text-secondary mb-3">
        <span className="font-mono font-black text-primary text-lg">R${(s.price_cents / 100).toFixed(0)}<span className="text-secondary text-[10px]">/{s.period_days}d</span></span>
        <span className="bg-bg-primary px-2 py-1 rounded-lg">{s.sessions_used}/{s.sessions_included} sessões</span>
        <span className="flex items-center gap-1"><Calendar className="w-3 h-3" />{new Date(s.current_period_end).toLocaleDateString('pt-BR')}</span>
      </div>
      <div className="w-full bg-bg-primary rounded-full h-1.5 mb-3">
        <div className="bg-accent-amethyst h-1.5 rounded-full transition-all" style={{ width: `${Math.min(100, (s.sessions_used / s.sessions_included) * 100)}%` }} />
      </div>
      <div className="flex gap-2">
        {s.status === 'active' && <button onClick={() => pauseMut.mutate()} className="flex items-center gap-1 px-3 py-1.5 bg-amber-500/10 text-amber-400 rounded-xl text-[10px] font-black uppercase tracking-widest"><Pause className="w-3 h-3" />Pausar</button>}
        {s.status === 'paused' && <button onClick={() => resumeMut.mutate()} className="flex items-center gap-1 px-3 py-1.5 bg-emerald-500/10 text-emerald-500 rounded-xl text-[10px] font-black uppercase tracking-widest"><Play className="w-3 h-3" />Retomar</button>}
        {s.status === 'expired' && <button onClick={() => renewMut.mutate()} className="flex items-center gap-1 px-3 py-1.5 bg-accent-amethyst/10 text-accent-amethyst rounded-xl text-[10px] font-black uppercase tracking-widest"><RefreshCw className="w-3 h-3" />Renovar</button>}
      </div>
    </div>
  );
}

function CreateSubModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [form, setForm] = useState({ package_name: '', sessions_included: 4, price_cents: 80000, period_days: 30 });
  const set = (k: string, v: unknown) => setForm(f => ({ ...f, [k]: v }));
  const createMut = useMutation({
    mutationFn: () => subscriptionsApi.create(form),
    onSuccess: () => { toast.success('Pacote criado!'); onCreated(); },
    onError: handleApiError('Erro ao criar'),
  });

  return (
    <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-6">
      <div className="bg-bg-surface border border-border rounded-3xl p-8 max-w-md w-full space-y-5">
        <h2 className="text-xl font-black tracking-tight">Novo Pacote</h2>
        <F label="Nome"><input value={form.package_name} onChange={e => set('package_name', e.target.value)} placeholder="Pacote Premium Mensal" className="inp" /></F>
        <div className="grid grid-cols-2 gap-3">
          <F label="Sessões incluídas"><input type="number" value={form.sessions_included} onChange={e => set('sessions_included', +e.target.value)} className="inp" /></F>
          <F label="Preço (R$)"><input type="number" value={form.price_cents / 100} onChange={e => set('price_cents', Math.round(+e.target.value * 100))} step={0.01} className="inp" /></F>
        </div>
        <F label="Período">
          <div className="flex gap-2">{[7, 15, 30, 60, 90].map(d => (
            <button key={d} onClick={() => set('period_days', d)} className={`flex-1 px-2 py-2 rounded-xl text-xs font-bold ${form.period_days === d ? 'bg-accent-amethyst text-white' : 'bg-bg-primary text-secondary'}`}>{d}d</button>
          ))}</div>
        </F>
        <div className="flex gap-3">
          <button onClick={onClose} className="flex-1 px-5 py-3 bg-bg-primary border border-border rounded-2xl text-sm font-bold">Cancelar</button>
          <button onClick={() => createMut.mutate()} disabled={!form.package_name || createMut.isPending} className="flex-1 px-5 py-3 bg-accent-amethyst hover:bg-accent-amethyst/90 disabled:opacity-30 text-white rounded-2xl text-sm font-black uppercase tracking-widest">
            {createMut.isPending ? 'Criando...' : 'Criar Pacote'}
          </button>
        </div>
      </div>
    </div>
  );
}

function F({ label, children }: { label: string; children: React.ReactNode }) {
  return <div><label className="text-[10px] uppercase font-black tracking-widest text-secondary mb-1.5 block">{label}</label>{children}</div>;
}
