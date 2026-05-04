import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Rocket, Plus, Play, Pause, Clock, ChevronDown, ChevronUp, Send, Copy, Trash2, Image, Edit3 } from 'lucide-react';
import { api } from '../api/client';
import { toast } from '../lib/toast';

const L = {
  list: () => api.get<{ launches: any[] }>('/saas/launch/'),
  get: (id: number) => api.get<any>(`/saas/launch/${id}`),
  create: (b: any) => api.post<any>('/saas/launch/', b),
  update: (id: number, b: any) => api.put<any>(`/saas/launch/${id}`, b),
  remove: (id: number) => api.del<any>(`/saas/launch/${id}`),
  templates: () => api.get<{ templates: any[] }>('/saas/launch/templates'),
  activate: (id: number) => api.post<any>(`/saas/launch/${id}/activate`, {}),
  pause: (id: number) => api.post<any>(`/saas/launch/${id}/pause`, {}),
  clone: (id: number) => api.post<any>(`/saas/launch/${id}/clone`, {}),
  test: (id: number) => api.post<any>(`/saas/launch/${id}/test`, {}),
  addPhase: (id: number, b: any) => api.post<any>(`/saas/launch/${id}/phases`, b),
  updatePhase: (id: number, pid: number, b: any) => api.put<any>(`/saas/launch/${id}/phases/${pid}`, b),
  deletePhase: (id: number, pid: number) => api.del<any>(`/saas/launch/${id}/phases/${pid}`),
  executePhase: (id: number, pid: number) => api.post<any>(`/saas/launch/${id}/execute-phase/${pid}`, {}),
};

const PHASE_ICONS: Record<string, string> = { warmup: '🔥', cart_open: '🛒', reminder: '⏰', scarcity: '🔴', cart_close: '🔒', custom: '⚙️' };
const STATUS_STYLES: Record<string, string> = { pending: 'bg-zinc-800 text-zinc-400', executed: 'bg-emerald-500/10 text-emerald-400', failed: 'bg-red-500/10 text-red-400', skipped: 'bg-zinc-700 text-zinc-500' };
const PHASE_TYPES = ['warmup', 'cart_open', 'reminder', 'scarcity', 'cart_close', 'custom'];

export default function LaunchManager() {
  const qc = useQueryClient();
  const [view, setView] = useState<'list' | 'create' | 'detail'>('list');
  const [selectedId, setSelectedId] = useState<number | null>(null);

  return (
    <div className="p-10 max-w-5xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-orange-500 to-red-500 flex items-center justify-center"><Rocket className="w-5 h-5 text-white" /></div>
          <div>
            <h1 className="text-3xl font-black tracking-tight">Lançamentos</h1>
            <p className="text-secondary text-sm">Gerencie lançamentos com grupos WhatsApp</p>
          </div>
        </div>
        {view === 'list' ? (
          <button onClick={() => setView('create')} className="flex items-center gap-2 px-5 py-3 bg-gradient-to-r from-orange-500 to-red-500 text-white rounded-xl font-black text-sm"><Plus className="w-4 h-4" /> Novo Lançamento</button>
        ) : (
          <button onClick={() => { setView('list'); setSelectedId(null); }} className="px-4 py-2 bg-bg-surface border border-border rounded-xl text-sm font-bold">← Voltar</button>
        )}
      </div>
      {view === 'list' && <LaunchList onSelect={(id) => { setSelectedId(id); setView('detail'); }} />}
      {view === 'create' && <CreateLaunch onCreated={(id) => { setSelectedId(id); setView('detail'); qc.invalidateQueries({ queryKey: ['launches'] }); }} />}
      {view === 'detail' && selectedId && <LaunchDetail id={selectedId} />}
    </div>
  );
}

function LaunchList({ onSelect }: { onSelect: (id: number) => void }) {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ['launches'], queryFn: L.list });
  const cloneMut = useMutation({ mutationFn: (id: number) => L.clone(id), onSuccess: (r) => { toast.success('Lançamento duplicado!'); qc.invalidateQueries({ queryKey: ['launches'] }); onSelect(r.id); } });
  const delMut = useMutation({ mutationFn: (id: number) => L.remove(id), onSuccess: () => { toast.success('Apagado'); qc.invalidateQueries({ queryKey: ['launches'] }); } });

  if (isLoading) return <div className="animate-pulse space-y-3">{[1,2,3].map(i => <div key={i} className="h-24 bg-bg-surface rounded-2xl" />)}</div>;
  const launches = data?.launches ?? [];
  if (!launches.length) return (
    <div className="text-center py-20 space-y-4">
      <div className="text-6xl">🚀</div>
      <h3 className="text-xl font-black">Nenhum lançamento ainda</h3>
      <p className="text-secondary text-sm max-w-md mx-auto">Crie seu primeiro lançamento, configure as fases com data/hora, conecte o grupo WhatsApp e veja a mágica acontecer.</p>
    </div>
  );
  return (
    <div className="space-y-3">
      {launches.map((l: any) => (
        <div key={l.id} className="bg-bg-surface border border-border rounded-2xl p-5 flex items-center gap-4 hover:border-accent-amethyst/30 transition-all group">
          <button onClick={() => onSelect(l.id)} className="flex items-center gap-4 flex-1 text-left min-w-0">
            <div className="text-3xl">{l.status === 'active' ? '🟢' : l.status === 'paused' ? '⏸️' : l.status === 'completed' ? '✅' : '📋'}</div>
            <div className="flex-1 min-w-0">
              <div className="font-black text-lg group-hover:text-accent-amethyst transition-colors">{l.name}</div>
              <div className="text-xs text-secondary flex gap-3 mt-1">
                <span>{l.total_phases} fases</span>
                <span>{l.executed_phases} executadas</span>
                {l.start_date && <span>Início: {new Date(l.start_date).toLocaleDateString('pt-BR')}</span>}
              </div>
            </div>
          </button>
          <div className="flex gap-1">
            <button onClick={() => cloneMut.mutate(l.id)} title="Duplicar" className="p-2 rounded-lg hover:bg-bg-primary"><Copy className="w-4 h-4 text-secondary" /></button>
            <button onClick={() => { if (confirm('Apagar este lançamento?')) delMut.mutate(l.id); }} title="Apagar" className="p-2 rounded-lg hover:bg-red-500/10"><Trash2 className="w-4 h-4 text-red-400" /></button>
          </div>
          <span className={`text-[9px] font-black uppercase tracking-widest px-3 py-1 rounded-full ${l.status === 'active' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-bg-primary text-secondary'}`}>{l.status}</span>
        </div>
      ))}
    </div>
  );
}

function CreateLaunch({ onCreated }: { onCreated: (id: number) => void }) {
  const [form, setForm] = useState({ name: '', product_name: '', group_jid: '', link_vendas: '', preco_lancamento: '', preco_normal: '', start_date: '', template_id: 'classico_7d', description: '' });
  const { data: tplData } = useQuery({ queryKey: ['launch-templates'], queryFn: L.templates });
  const templates = tplData?.templates ?? [];
  const set = (k: string, v: string) => setForm(f => ({ ...f, [k]: v }));
  const mut = useMutation({ mutationFn: () => L.create(form), onSuccess: (r) => { toast.success('Lançamento criado!'); onCreated(r.id); }, onError: () => toast.error('Erro ao criar') });

  return (
    <div className="bg-bg-surface border border-border rounded-3xl p-8 space-y-6">
      <h2 className="font-black text-xl">Novo Lançamento</h2>
      <div className="grid grid-cols-2 gap-4">
        <F label="Nome do Lançamento"><input value={form.name} onChange={e => set('name', e.target.value)} placeholder="Ex: Lançamento Consulta VIP" className="inp" /></F>
        <F label="Nome do Produto"><input value={form.product_name} onChange={e => set('product_name', e.target.value)} placeholder="Consulta VIP" className="inp" /></F>
        <F label="ID do Grupo WhatsApp"><input value={form.group_jid} onChange={e => set('group_jid', e.target.value)} placeholder="5511999...@g.us" className="inp" /></F>
        <F label="Link de Vendas"><input value={form.link_vendas} onChange={e => set('link_vendas', e.target.value)} placeholder="https://..." className="inp" /></F>
        <F label="Preço Lançamento"><input value={form.preco_lancamento} onChange={e => set('preco_lancamento', e.target.value)} placeholder="297" className="inp" /></F>
        <F label="Preço Normal"><input value={form.preco_normal} onChange={e => set('preco_normal', e.target.value)} placeholder="497" className="inp" /></F>
        <F label="Data de Início"><input type="datetime-local" value={form.start_date} onChange={e => set('start_date', e.target.value)} className="inp" /></F>
        <F label="Template">
          <select value={form.template_id} onChange={e => set('template_id', e.target.value)} className="inp">
            <option value="">Sem template</option>
            {templates.map((t: any) => <option key={t.id} value={t.id}>{t.name} — {t.phases.length} fases</option>)}
          </select>
        </F>
      </div>
      <F label="Descrição (opcional)"><textarea value={form.description} onChange={e => set('description', e.target.value)} rows={2} placeholder="Detalhes internos do lançamento..." className="inp" /></F>
      {form.template_id && templates.find((t: any) => t.id === form.template_id) && (
        <div className="bg-bg-primary border border-border rounded-xl p-4 space-y-2">
          <h4 className="text-xs font-black uppercase text-secondary">Preview das fases:</h4>
          {templates.find((t: any) => t.id === form.template_id)?.phases.map((p: any, i: number) => (
            <div key={i} className="flex items-center gap-2 text-xs"><span>{PHASE_ICONS[p.phase_type] || '⚙️'}</span><span className="font-bold">{p.name}</span><span className="text-secondary ml-auto">+{p.offset_hours}h</span></div>
          ))}
        </div>
      )}
      <button onClick={() => mut.mutate()} disabled={!form.name || !form.start_date || mut.isPending}
        className="w-full py-4 bg-gradient-to-r from-orange-500 to-red-500 disabled:opacity-30 text-white rounded-2xl font-black text-sm uppercase tracking-widest">
        {mut.isPending ? 'Criando...' : '🚀 Criar Lançamento'}
      </button>
    </div>
  );
}

function LaunchDetail({ id }: { id: number }) {
  const qc = useQueryClient();
  const inv = () => qc.invalidateQueries({ queryKey: ['launch', id] });
  const { data, isLoading } = useQuery({ queryKey: ['launch', id], queryFn: () => L.get(id) });
  const [expanded, setExpanded] = useState<number | null>(null);
  const [adding, setAdding] = useState(false);
  const [editing, setEditing] = useState<number | null>(null);
  const [editForm, setEditForm] = useState({ name: '', phase_type: 'custom', scheduled_at: '', group_name_template: '', message_template: '', media_url: '' });

  const activateMut = useMutation({ mutationFn: () => L.activate(id), onSuccess: () => { toast.success('Ativado!'); inv(); } });
  const pauseMut = useMutation({ mutationFn: () => L.pause(id), onSuccess: () => { toast.success('Pausado'); inv(); } });
  const testMut = useMutation({ mutationFn: () => L.test(id), onSuccess: (r) => toast.success(r.message || 'Teste enviado!'), onError: () => toast.error('Falha no teste') });
  const execMut = useMutation({ mutationFn: (pid: number) => L.executePhase(id, pid), onSuccess: () => { toast.success('Fase executada!'); inv(); } });
  const delPhaseMut = useMutation({ mutationFn: (pid: number) => L.deletePhase(id, pid), onSuccess: () => { toast.success('Removida'); inv(); } });
  const addPhaseMut = useMutation({ mutationFn: (b: any) => L.addPhase(id, b), onSuccess: () => { toast.success('Fase adicionada!'); setAdding(false); inv(); } });
  const updPhaseMut = useMutation({ mutationFn: ({ pid, b }: { pid: number; b: any }) => L.updatePhase(id, pid, b), onSuccess: () => { toast.success('Salvo!'); setEditing(null); inv(); } });

  if (isLoading || !data) return <div className="animate-pulse h-96 bg-bg-surface rounded-3xl" />;
  const l = data;

  const startEdit = (p: any) => { setEditing(p.id); setEditForm({ name: p.name, phase_type: p.phase_type, scheduled_at: p.scheduled_at?.slice(0, 16) || '', group_name_template: p.group_name_template || '', message_template: p.message_template || '', media_url: p.media_url || '' }); };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-bg-surface border border-border rounded-3xl p-6 flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-black">{l.name}</h2>
          <div className="flex gap-3 text-xs text-secondary mt-1">
            <span>📦 {l.product_name}</span>
            {l.start_date && <span>📅 {new Date(l.start_date).toLocaleString('pt-BR')}</span>}
            <span className={`font-black uppercase ${l.status === 'active' ? 'text-emerald-400' : ''}`}>{l.status}</span>
          </div>
        </div>
        <div className="flex gap-2">
          <button onClick={() => testMut.mutate()} disabled={testMut.isPending} className="flex items-center gap-1 px-3 py-2 bg-blue-500/10 text-blue-400 border border-blue-500/20 rounded-xl text-xs font-black" title="Enviar teste pra você">
            📲 {testMut.isPending ? '...' : 'Testar'}
          </button>
          {l.status !== 'active' && <button onClick={() => activateMut.mutate()} className="flex items-center gap-1 px-4 py-2 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-xl text-xs font-black"><Play className="w-3 h-3" /> Ativar</button>}
          {l.status === 'active' && <button onClick={() => pauseMut.mutate()} className="flex items-center gap-1 px-4 py-2 bg-amber-500/10 text-amber-400 border border-amber-500/20 rounded-xl text-xs font-black"><Pause className="w-3 h-3" /> Pausar</button>}
        </div>
      </div>

      {/* Progress */}
      <div className="bg-bg-surface border border-border rounded-2xl p-4">
        <div className="flex items-center justify-between text-xs mb-2">
          <span className="font-black text-secondary">Progresso</span>
          <span className="font-black text-accent-amethyst">{l.executed_phases}/{l.total_phases}</span>
        </div>
        <div className="h-3 bg-bg-primary rounded-full overflow-hidden">
          <div className="h-full bg-gradient-to-r from-orange-500 to-red-500 rounded-full transition-all" style={{ width: `${l.total_phases ? (l.executed_phases / l.total_phases * 100) : 0}%` }} />
        </div>
      </div>

      {/* Timeline */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <h3 className="font-black text-sm flex items-center gap-2"><Clock className="w-4 h-4" /> Timeline ({l.total_phases} fases)</h3>
          <button onClick={() => { setAdding(true); setEditForm({ name: '', phase_type: 'custom', scheduled_at: '', group_name_template: '', message_template: '', media_url: '' }); }} className="flex items-center gap-1 text-xs font-bold text-accent-amethyst"><Plus className="w-3 h-3" /> Nova Fase</button>
        </div>

        {adding && <PhaseForm form={editForm} setForm={setEditForm} onSave={() => addPhaseMut.mutate(editForm)} onCancel={() => setAdding(false)} saving={addPhaseMut.isPending} />}

        {(l.phases || []).map((p: any) => (
          <div key={p.id} className="bg-bg-surface border border-border rounded-xl overflow-hidden">
            {editing === p.id ? (
              <div className="p-4"><PhaseForm form={editForm} setForm={setEditForm} onSave={() => updPhaseMut.mutate({ pid: p.id, b: editForm })} onCancel={() => setEditing(null)} saving={updPhaseMut.isPending} /></div>
            ) : (
              <>
                <button onClick={() => setExpanded(expanded === p.id ? null : p.id)} className="w-full p-4 flex items-center gap-3 text-left hover:bg-bg-primary/30 transition-colors">
                  <span className="text-xl">{PHASE_ICONS[p.phase_type] || '⚙️'}</span>
                  <div className="flex-1 min-w-0">
                    <div className="font-bold text-sm">{p.name}</div>
                    <div className="text-[10px] text-secondary">{p.scheduled_at ? new Date(p.scheduled_at).toLocaleString('pt-BR') : 'Sem data'}</div>
                  </div>
                  <span className={`text-[9px] font-black uppercase tracking-widest px-2 py-0.5 rounded-full ${STATUS_STYLES[p.status] || ''}`}>{p.status === 'executed' ? '✅' : p.status}</span>
                  {expanded === p.id ? <ChevronUp className="w-4 h-4 text-secondary" /> : <ChevronDown className="w-4 h-4 text-secondary" />}
                </button>
                {expanded === p.id && (
                  <div className="border-t border-border p-4 space-y-3 bg-bg-primary/20">
                    {p.group_name_template && <div><span className="text-[9px] font-black uppercase text-secondary">Nome do grupo:</span><div className="text-sm font-bold mt-1">{p.group_name_template}</div></div>}
                    {p.message_template && <div><span className="text-[9px] font-black uppercase text-secondary">Mensagem:</span><div className="text-xs whitespace-pre-wrap bg-bg-surface rounded-xl p-3 mt-1 border border-border max-h-40 overflow-y-auto">{p.message_template}</div></div>}
                    {p.media_url && <div><span className="text-[9px] font-black uppercase text-secondary">Mídia:</span><div className="text-xs text-blue-400 mt-1 truncate">{p.media_url}</div></div>}
                    {p.executed_at && <div className="text-[10px] text-emerald-400">✅ Executado em {new Date(p.executed_at).toLocaleString('pt-BR')}</div>}
                    <div className="flex gap-2">
                      {p.status === 'pending' && <button onClick={() => execMut.mutate(p.id)} disabled={execMut.isPending} className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-orange-500 to-red-500 text-white rounded-xl text-xs font-black disabled:opacity-30"><Send className="w-3 h-3" /> Executar</button>}
                      <button onClick={() => startEdit(p)} className="flex items-center gap-1 px-3 py-2 bg-bg-surface border border-border rounded-xl text-xs font-bold"><Edit3 className="w-3 h-3" /> Editar</button>
                      <button onClick={() => { if (confirm('Remover esta fase?')) delPhaseMut.mutate(p.id); }} className="flex items-center gap-1 px-3 py-2 bg-red-500/10 text-red-400 border border-red-500/20 rounded-xl text-xs font-bold"><Trash2 className="w-3 h-3" /> Remover</button>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        ))}
      </div>

      {/* Info */}
      <div className="bg-bg-surface border border-border rounded-2xl p-5 grid grid-cols-2 gap-4 text-xs">
        <div><span className="font-black text-secondary uppercase text-[9px]">Grupo</span><div className="font-mono mt-1">{l.group_jid || '—'}</div></div>
        <div><span className="font-black text-secondary uppercase text-[9px]">Link Vendas</span><div className="font-mono mt-1 truncate">{l.link_vendas || '—'}</div></div>
        <div><span className="font-black text-secondary uppercase text-[9px]">Preço Lançamento</span><div className="mt-1">R$ {l.preco_lancamento || '—'}</div></div>
        <div><span className="font-black text-secondary uppercase text-[9px]">Preço Normal</span><div className="mt-1">R$ {l.preco_normal || '—'}</div></div>
      </div>
    </div>
  );
}

function PhaseForm({ form, setForm, onSave, onCancel, saving }: { form: any; setForm: (f: any) => void; onSave: () => void; onCancel: () => void; saving: boolean }) {
  const set = (k: string, v: string) => setForm((f: any) => ({ ...f, [k]: v }));
  return (
    <div className="bg-bg-primary border border-border rounded-xl p-4 space-y-3">
      <div className="grid grid-cols-3 gap-3">
        <F label="Nome"><input value={form.name} onChange={e => set('name', e.target.value)} placeholder="Nome da fase" className="inp" /></F>
        <F label="Tipo"><select value={form.phase_type} onChange={e => set('phase_type', e.target.value)} className="inp">{PHASE_TYPES.map(t => <option key={t} value={t}>{PHASE_ICONS[t]} {t}</option>)}</select></F>
        <F label="Data/Hora"><input type="datetime-local" value={form.scheduled_at} onChange={e => set('scheduled_at', e.target.value)} className="inp" /></F>
      </div>
      <F label="Nome do grupo nesta fase"><input value={form.group_name_template} onChange={e => set('group_name_template', e.target.value)} placeholder="🛒 [NOME] — ABERTO! 🔥" className="inp" /></F>
      <F label="Mensagem"><textarea value={form.message_template} onChange={e => set('message_template', e.target.value)} rows={4} placeholder="Use {link_vendas}, {preco_lancamento}, {preco_normal}, {produto}..." className="inp" /></F>
      <F label="URL da mídia (imagem/vídeo — opcional)"><input value={form.media_url} onChange={e => set('media_url', e.target.value)} placeholder="https://..." className="inp" /></F>
      <div className="flex gap-2">
        <button onClick={onSave} disabled={!form.name || saving} className="px-4 py-2 bg-accent-amethyst disabled:opacity-30 text-white rounded-xl text-xs font-black">{saving ? 'Salvando...' : '💾 Salvar'}</button>
        <button onClick={onCancel} className="px-4 py-2 bg-bg-surface border border-border rounded-xl text-xs font-bold">Cancelar</button>
      </div>
    </div>
  );
}

function F({ label, children }: { label: string; children: React.ReactNode }) {
  return <div><label className="text-[10px] uppercase font-black tracking-widest text-secondary mb-1.5 block">{label}</label>{children}</div>;
}
