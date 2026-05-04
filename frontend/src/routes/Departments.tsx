import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Building2, Plus, Trash2, ArrowRightLeft, Clock, Star,
  BarChart3, RefreshCw, Users, ClipboardCheck, MessageSquare
} from 'lucide-react';
import { api } from '../api/client';
import { toast } from '../lib/toast';

type Dept = {
  id: number; name: string; slug: string; emoji: string;
  description: string | null; auto_reply: string | null; sort_order: number;
};

export default function Departments() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<'departments' | 'queue' | 'hours' | 'transfers'>('departments');
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ name: '', slug: '', emoji: '📋', description: '', auto_reply: '' });

  const { data: depts } = useQuery({
    queryKey: ['departments'],
    queryFn: () => api.get<{ departments: Dept[] }>('/saas/atendimento/departments'),
  });

  const { data: queueData } = useQuery({
    queryKey: ['queue'],
    queryFn: () => api.get<{ queue: any[]; total_waiting: number }>('/saas/atendimento/queue'),
    enabled: tab === 'queue',
  });

  const { data: hoursData } = useQuery({
    queryKey: ['business-hours'],
    queryFn: () => api.get<{ hours: any; is_open: boolean; current_day: string }>('/saas/atendimento/business-hours'),
    enabled: tab === 'hours',
  });

  const { data: transfersData } = useQuery({
    queryKey: ['transfers'],
    queryFn: () => api.get<{ transfers: any[] }>('/saas/atendimento/transfers'),
    enabled: tab === 'transfers',
  });

  const createMut = useMutation({
    mutationFn: (d: any) => api.post('/saas/atendimento/departments', d),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['departments'] }); toast.success('Departamento criado!'); setShowCreate(false); },
  });

  const deleteMut = useMutation({
    mutationFn: (id: number) => api.delete(`/saas/atendimento/departments/${id}`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['departments'] }); toast.success('Departamento removido'); },
  });

  const serveMut = useMutation({
    mutationFn: (id: number) => api.post(`/saas/atendimento/queue/${id}/serve`, {}),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['queue'] }); toast.success('Atendendo!'); },
  });

  const saveHoursMut = useMutation({
    mutationFn: (d: any) => api.post('/saas/atendimento/business-hours', d),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['business-hours'] }); toast.success('Horários salvos!'); },
  });

  const [hoursForm, setHoursForm] = useState({
    timezone: 'America/Sao_Paulo',
    away_message: 'Olá! 💜 Nosso atendimento é de seg-sex 9h-18h. Recebemos sua mensagem e responderemos no próximo horário útil ✨',
    schedule: {
      mon: { start: '09:00', end: '18:00' },
      tue: { start: '09:00', end: '18:00' },
      wed: { start: '09:00', end: '18:00' },
      thu: { start: '09:00', end: '18:00' },
      fri: { start: '09:00', end: '18:00' },
    } as Record<string, { start: string; end: string }>,
  });

  const dayLabels: Record<string, string> = {
    mon: 'Segunda', tue: 'Terça', wed: 'Quarta', thu: 'Quinta', fri: 'Sexta', sat: 'Sábado', sun: 'Domingo',
  };

  return (
    <div className="px-8 py-8 max-w-[1400px] mx-auto min-h-screen">
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-lg">
            <Building2 className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="font-display text-3xl text-primary tracking-tight">Multi-Atendimento</h1>
            <p className="text-xs text-secondary">Departamentos, fila, horários e transferências</p>
          </div>
        </div>
        {tab === 'departments' && (
          <button onClick={() => setShowCreate(true)} className="flex items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-indigo-500 to-purple-600 text-white rounded-xl text-xs font-bold shadow-lg hover:scale-105 transition-all">
            <Plus className="w-4 h-4" /> Novo Departamento
          </button>
        )}
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 bg-bg-sidebar p-1 rounded-2xl border border-border mb-6 w-fit">
        {([
          { key: 'departments', label: 'Departamentos', icon: Building2 },
          { key: 'queue', label: 'Fila de Espera', icon: Users },
          { key: 'hours', label: 'Horários', icon: Clock },
          { key: 'transfers', label: 'Transferências', icon: ArrowRightLeft },
        ] as const).map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold transition-all ${
              tab === t.key ? 'bg-bg-surface text-primary shadow-sm border border-border' : 'text-secondary hover:text-primary'
            }`}>
            <t.icon className="w-4 h-4" /> {t.label}
          </button>
        ))}
      </div>

      {/* DEPARTMENTS */}
      {tab === 'departments' && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {(depts?.departments || []).map(d => (
            <div key={d.id} className="bg-bg-surface border border-border rounded-2xl p-5 hover:border-indigo-500/30 transition-all group">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <span className="text-2xl">{d.emoji}</span>
                  <div>
                    <h3 className="font-bold text-sm text-primary">{d.name}</h3>
                    <span className="text-[9px] text-secondary font-mono">{d.slug}</span>
                  </div>
                </div>
                <button onClick={() => deleteMut.mutate(d.id)} className="opacity-0 group-hover:opacity-100 text-rose-400">
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
              {d.description && <p className="text-xs text-secondary mb-2">{d.description}</p>}
              {d.auto_reply && (
                <div className="text-[10px] text-secondary/70 bg-bg-sidebar p-2 rounded-lg">
                  <MessageSquare className="w-3 h-3 inline mr-1" /> {d.auto_reply.substring(0, 100)}...
                </div>
              )}
            </div>
          ))}
          {(!depts?.departments?.length) && (
            <div className="col-span-3 text-center py-20 text-secondary">
              <Building2 className="w-12 h-12 mx-auto mb-4 opacity-30" />
              <p className="text-sm">Nenhum departamento criado.</p>
              <p className="text-xs mt-1">Crie departamentos como "Consultas", "Cursos" ou "Suporte".</p>
            </div>
          )}
        </div>
      )}

      {/* QUEUE */}
      {tab === 'queue' && (
        <div className="space-y-3">
          <div className="bg-bg-surface border border-border rounded-2xl p-4 flex items-center gap-4 mb-4">
            <Users className="w-6 h-6 text-amber-500" />
            <div>
              <span className="text-sm font-bold text-primary">{queueData?.total_waiting || 0}</span>
              <span className="text-xs text-secondary ml-2">pessoas na fila</span>
            </div>
          </div>
          {(queueData?.queue || []).map((e: any) => (
            <div key={e.id} className="bg-bg-surface border border-border rounded-xl p-4 flex items-center gap-4">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-amber-500 to-orange-500 flex items-center justify-center text-white font-bold text-xs">
                {e.position}
              </div>
              <div className="flex-1">
                <div className="text-sm font-bold text-primary">{e.lead_name}</div>
                <div className="text-[10px] text-secondary">Esperando há {e.wait_minutes} min</div>
              </div>
              <button onClick={() => serveMut.mutate(e.id)} className="px-4 py-2 bg-gradient-to-r from-emerald-500 to-green-600 text-white rounded-xl text-xs font-bold">
                Atender
              </button>
            </div>
          ))}
          {(!queueData?.queue?.length) && (
            <div className="text-center py-12 text-secondary text-xs">Fila vazia ✨</div>
          )}
        </div>
      )}

      {/* BUSINESS HOURS */}
      {tab === 'hours' && (
        <div className="bg-bg-surface border border-border rounded-2xl p-6 max-w-xl">
          <div className="flex items-center gap-3 mb-4">
            <Clock className="w-5 h-5 text-indigo-500" />
            <h3 className="font-bold text-lg text-primary">Horário de Atendimento</h3>
            {hoursData && (
              <span className={`text-xs font-bold px-2 py-1 rounded ${hoursData.is_open ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'}`}>
                {hoursData.is_open ? '🟢 Aberto' : '🔴 Fechado'}
              </span>
            )}
          </div>
          <div className="space-y-3 mb-4">
            {Object.entries(dayLabels).map(([key, label]) => (
              <div key={key} className="flex items-center gap-3">
                <label className="w-20 text-xs font-bold text-primary">{label}</label>
                <input type="checkbox" checked={!!hoursForm.schedule[key]}
                  onChange={e => {
                    const s = { ...hoursForm.schedule };
                    if (e.target.checked) s[key] = { start: '09:00', end: '18:00' };
                    else delete s[key];
                    setHoursForm({ ...hoursForm, schedule: s });
                  }}
                  className="rounded" />
                {hoursForm.schedule[key] && (
                  <>
                    <input type="time" value={hoursForm.schedule[key]?.start || '09:00'}
                      onChange={e => setHoursForm({ ...hoursForm, schedule: { ...hoursForm.schedule, [key]: { ...hoursForm.schedule[key], start: e.target.value } } })}
                      className="px-2 py-1 bg-bg-sidebar border border-border rounded text-xs text-primary" />
                    <span className="text-xs text-secondary">até</span>
                    <input type="time" value={hoursForm.schedule[key]?.end || '18:00'}
                      onChange={e => setHoursForm({ ...hoursForm, schedule: { ...hoursForm.schedule, [key]: { ...hoursForm.schedule[key], end: e.target.value } } })}
                      className="px-2 py-1 bg-bg-sidebar border border-border rounded text-xs text-primary" />
                  </>
                )}
              </div>
            ))}
          </div>
          <textarea placeholder="Mensagem fora do horário" value={hoursForm.away_message}
            onChange={e => setHoursForm({ ...hoursForm, away_message: e.target.value })}
            className="w-full px-4 py-2.5 bg-bg-sidebar border border-border rounded-xl text-sm text-primary placeholder:text-secondary/50 focus:outline-none focus:border-indigo-500 resize-none mb-4" rows={3} />
          <button onClick={() => saveHoursMut.mutate(hoursForm)} disabled={saveHoursMut.isPending}
            className="w-full py-2.5 bg-gradient-to-r from-indigo-500 to-purple-600 text-white rounded-xl text-xs font-bold shadow-lg">
            {saveHoursMut.isPending ? 'Salvando...' : 'Salvar Horários'}
          </button>
        </div>
      )}

      {/* TRANSFERS */}
      {tab === 'transfers' && (
        <div className="space-y-3">
          {(transfersData?.transfers || []).map((t: any) => (
            <div key={t.id} className="bg-bg-surface border border-border rounded-xl p-4 flex items-center gap-4">
              <ArrowRightLeft className="w-5 h-5 text-indigo-400" />
              <div className="flex-1">
                <div className="text-sm font-bold text-primary">{t.lead_name}</div>
                <div className="text-[10px] text-secondary">
                  Atendente #{t.from_user_id} → {t.to_user_id ? `Atendente #${t.to_user_id}` : `Dept #${t.to_department_id}`}
                  {t.reason && ` • "${t.reason}"`}
                </div>
              </div>
              <div className="text-[10px] text-secondary">
                {t.transferred_at && new Date(t.transferred_at).toLocaleDateString('pt-BR')}
              </div>
            </div>
          ))}
          {(!transfersData?.transfers?.length) && (
            <div className="text-center py-12 text-secondary text-xs">Nenhuma transferência registrada</div>
          )}
        </div>
      )}

      {/* CREATE MODAL */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowCreate(false)}>
          <div className="bg-bg-surface border border-border rounded-2xl p-6 w-full max-w-md" onClick={e => e.stopPropagation()}>
            <h2 className="font-bold text-lg text-primary mb-4">Novo Departamento</h2>
            <div className="space-y-3">
              <input placeholder="Nome (ex: Consultas)" value={form.name} onChange={e => setForm({ ...form, name: e.target.value, slug: e.target.value.toLowerCase().replace(/\s+/g, '_') })}
                className="w-full px-4 py-2.5 bg-bg-sidebar border border-border rounded-xl text-sm text-primary placeholder:text-secondary/50 focus:outline-none focus:border-indigo-500" />
              <input placeholder="Emoji" value={form.emoji} onChange={e => setForm({ ...form, emoji: e.target.value })}
                className="w-20 px-4 py-2.5 bg-bg-sidebar border border-border rounded-xl text-sm text-center" />
              <textarea placeholder="Mensagem automática ao direcionar" value={form.auto_reply} onChange={e => setForm({ ...form, auto_reply: e.target.value })}
                className="w-full px-4 py-2.5 bg-bg-sidebar border border-border rounded-xl text-sm text-primary placeholder:text-secondary/50 focus:outline-none focus:border-indigo-500 resize-none" rows={3} />
              <button onClick={() => createMut.mutate(form)} disabled={!form.name || createMut.isPending}
                className="w-full py-2.5 bg-gradient-to-r from-indigo-500 to-purple-600 text-white rounded-xl text-xs font-bold shadow-lg">
                {createMut.isPending ? 'Criando...' : 'Criar Departamento'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
