import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  UsersRound, Plus, Send, Calendar, RefreshCw, Download,
  Copy, Trash2, MessageSquare, BarChart3, Users, Megaphone, AtSign, MousePointerClick
} from 'lucide-react';
import { api } from '../api/client';
import { toast } from '../lib/toast';

type WAGroup = {
  id: number; name: string; description: string | null;
  purpose: string; launch_id: number | null;
  max_members: number; current_members: number;
  active: boolean; invite_link: string | null;
  scheduled_messages: number; created_at: string | null;
};

export default function WAGroups() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<'groups' | 'dashboard'>('groups');
  const [showCreate, setShowCreate] = useState(false);
  const [showBulk, setShowBulk] = useState(false);
  const [showImport, setShowImport] = useState(false);
  const [showMention, setShowMention] = useState<number | null>(null);
  const [showButtons, setShowButtons] = useState<number | null>(null);
  const [mentionMsg, setMentionMsg] = useState('');
  const [btnForm, setBtnForm] = useState({ type: 'reply_buttons', body: '', header: '', footer: '', buttons: [{ id: 'btn1', title: '' }, { id: 'btn2', title: '' }], cta_url: '', cta_text: 'Acessar' });
  const [importText, setImportText] = useState('');
  const [form, setForm] = useState({ name: '', description: '', purpose: 'launch', invite_link: '' });
  const [bulkForm, setBulkForm] = useState({ name_template: 'Grupo {n}', count: 5, purpose: 'launch', description: '' });

  const { data, isLoading } = useQuery({
    queryKey: ['wa-groups'],
    queryFn: () => api.get<{ groups: WAGroup[]; total: number }>('/saas/groups/'),
  });

  const { data: dashData } = useQuery({
    queryKey: ['wa-groups-dash'],
    queryFn: () => api.get<{
      total_groups: number; total_members: number;
      by_purpose: Record<string, number>;
      pending_messages: number; sent_messages: number;
    }>('/saas/groups/dashboard'),
    enabled: tab === 'dashboard',
  });

  const createMut = useMutation({
    mutationFn: (d: any) => api.post('/saas/groups/', d),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['wa-groups'] }); toast.success('Grupo criado!'); setShowCreate(false); },
  });

  const bulkMut = useMutation({
    mutationFn: (d: any) => api.post('/saas/groups/bulk-create', d),
    onSuccess: (r: any) => { qc.invalidateQueries({ queryKey: ['wa-groups'] }); toast.success(`${r.total} grupos criados!`); setShowBulk(false); },
  });

  const deleteMut = useMutation({
    mutationFn: (id: number) => api.delete(`/saas/groups/${id}`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['wa-groups'] }); toast.success('Grupo removido'); },
  });

  const importMut = useMutation({
    mutationFn: (groups: any[]) => api.post('/saas/groups/import', { groups }),
    onSuccess: (r: any) => { qc.invalidateQueries({ queryKey: ['wa-groups'] }); toast.success(`${r.total} grupos importados!`); setShowImport(false); setImportText(''); },
    onError: () => toast.error('Erro ao importar. Conecte o WhatsApp primeiro.'),
  });

  const mentionMut = useMutation({
    mutationFn: ({ id, message }: { id: number; message: string }) => api.post(`/saas/groups/${id}/mention-all`, { message }),
    onSuccess: () => { toast.success('@todos enviado!'); setShowMention(null); setMentionMsg(''); },
    onError: () => toast.error('Erro ao enviar @todos'),
  });

  const buttonMut = useMutation({
    mutationFn: ({ id, ...body }: any) => api.post(`/saas/groups/${id}/send-buttons`, body),
    onSuccess: () => { toast.success('Mensagem com botões enviada!'); setShowButtons(null); },
    onError: () => toast.error('Erro ao enviar botões'),
  });

  const purposeLabels: Record<string, { label: string; emoji: string; color: string }> = {
    launch: { label: 'Lançamento', emoji: '🚀', color: 'from-orange-500 to-red-500' },
    community: { label: 'Comunidade', emoji: '🌍', color: 'from-blue-500 to-indigo-500' },
    vip: { label: 'VIP', emoji: '⭐', color: 'from-amber-500 to-yellow-500' },
    support: { label: 'Suporte', emoji: '🛟', color: 'from-green-500 to-emerald-500' },
    imported: { label: 'Importado', emoji: '📥', color: 'from-slate-500 to-zinc-500' },
  };

  return (
    <div className="px-8 py-8 max-w-[1400px] mx-auto min-h-screen">
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-green-500 to-emerald-600 flex items-center justify-center shadow-lg">
            <UsersRound className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="font-display text-3xl text-primary tracking-tight">Grupos WhatsApp</h1>
            <p className="text-xs text-secondary">{data?.total || 0} grupos gerenciados</p>
          </div>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setShowImport(true)} className="flex items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-emerald-500 to-teal-500 text-white rounded-xl text-xs font-bold shadow-lg hover:scale-105 transition-all">
            <Download className="w-4 h-4" /> Importar
          </button>
          <button onClick={() => setShowBulk(true)} className="flex items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-amber-500 to-orange-500 text-white rounded-xl text-xs font-bold shadow-lg hover:scale-105 transition-all">
            <Copy className="w-4 h-4" /> Criar em Massa
          </button>
          <button onClick={() => setShowCreate(true)} className="flex items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-indigo-500 to-purple-600 text-white rounded-xl text-xs font-bold shadow-lg hover:scale-105 transition-all">
            <Plus className="w-4 h-4" /> Novo Grupo
          </button>
        </div>
      </div>

      <div className="flex items-center gap-1 bg-bg-sidebar p-1 rounded-2xl border border-border mb-6 w-fit">
        {([
          { key: 'groups', label: 'Grupos', icon: UsersRound },
          { key: 'dashboard', label: 'Dashboard', icon: BarChart3 },
        ] as const).map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold transition-all ${
              tab === t.key ? 'bg-bg-surface text-primary shadow-sm border border-border' : 'text-secondary hover:text-primary'
            }`}>
            <t.icon className="w-4 h-4" /> {t.label}
          </button>
        ))}
      </div>

      {/* GROUPS TAB */}
      {tab === 'groups' && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {(data?.groups || []).map(g => {
            const meta = purposeLabels[g.purpose] || purposeLabels.launch;
            return (
              <div key={g.id} className="bg-bg-surface border border-border rounded-2xl p-5 hover:border-indigo-500/30 transition-all group">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${meta.color} flex items-center justify-center`}>
                      <span className="text-lg">{meta.emoji}</span>
                    </div>
                    <div>
                      <h3 className="font-bold text-sm text-primary">{g.name}</h3>
                      <span className="text-[9px] font-bold text-secondary uppercase">{meta.label}</span>
                    </div>
                  </div>
                  <button onClick={() => deleteMut.mutate(g.id)} className="opacity-0 group-hover:opacity-100 text-rose-400 hover:text-rose-300 transition-all">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
                {g.description && <p className="text-xs text-secondary mb-3 line-clamp-2">{g.description}</p>}
                <div className="flex items-center justify-between text-[10px] text-secondary">
                  <div className="flex items-center gap-3">
                    <span className="flex items-center gap-1"><Users className="w-3 h-3" /> {g.current_members}/{g.max_members}</span>
                    <span className="flex items-center gap-1"><Calendar className="w-3 h-3" /> {g.scheduled_messages} agendadas</span>
                  </div>
                  {g.invite_link && (
                    <a href={g.invite_link} target="_blank" className="text-indigo-400 hover:underline">Link</a>
                  )}
                </div>
                {/* Actions: @todos + Buttons */}
                <div className="flex gap-1.5 mt-3 pt-3 border-t border-border/50">
                  <button onClick={() => { setShowMention(g.id); setMentionMsg(''); }} className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-500/10 text-blue-400 border border-blue-500/20 rounded-lg text-[10px] font-bold hover:bg-blue-500/20 transition-all">
                    <AtSign className="w-3 h-3" /> @todos
                  </button>
                  <button onClick={() => { setShowButtons(g.id); setBtnForm({ type: 'reply_buttons', body: '', header: '', footer: '', buttons: [{ id: 'btn1', title: '' }, { id: 'btn2', title: '' }], cta_url: '', cta_text: 'Acessar' }); }} className="flex items-center gap-1.5 px-3 py-1.5 bg-purple-500/10 text-purple-400 border border-purple-500/20 rounded-lg text-[10px] font-bold hover:bg-purple-500/20 transition-all">
                    <MousePointerClick className="w-3 h-3" /> Botões
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* DASHBOARD TAB */}
      {tab === 'dashboard' && dashData && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            {[
              { label: 'Total Grupos', value: dashData.total_groups, icon: UsersRound },
              { label: 'Total Membros', value: dashData.total_members, icon: Users },
              { label: 'Msgs Pendentes', value: dashData.pending_messages, icon: Calendar },
              { label: 'Msgs Enviadas', value: dashData.sent_messages, icon: Send },
              { label: 'Tipos', value: Object.keys(dashData.by_purpose).length, icon: BarChart3 },
            ].map(kpi => (
              <div key={kpi.label} className="bg-bg-surface border border-border rounded-2xl p-5">
                <div className="text-xs text-secondary mb-2">{kpi.label}</div>
                <div className="text-2xl font-bold text-primary">{kpi.value}</div>
              </div>
            ))}
          </div>
          <div className="bg-bg-surface border border-border rounded-2xl p-6">
            <h3 className="font-bold text-sm text-primary mb-4">Por Propósito</h3>
            <div className="grid grid-cols-4 gap-4">
              {Object.entries(dashData.by_purpose).map(([k, v]) => {
                const meta = purposeLabels[k] || purposeLabels.launch;
                return (
                  <div key={k} className="text-center p-4 bg-bg-sidebar rounded-xl">
                    <div className="text-lg mb-1">{meta.emoji}</div>
                    <div className="text-xl font-bold text-primary">{v as number}</div>
                    <div className="text-[10px] text-secondary">{meta.label}</div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* CREATE MODAL */}
      {showCreate && (
        <Modal onClose={() => setShowCreate(false)} title="Novo Grupo">
          <div className="space-y-3">
            <input placeholder="Nome do grupo" value={form.name} onChange={e => setForm({...form, name: e.target.value})} className="inp" />
            <textarea placeholder="Descrição" value={form.description} onChange={e => setForm({...form, description: e.target.value})} className="inp" rows={3} />
            <select value={form.purpose} onChange={e => setForm({...form, purpose: e.target.value})} className="inp">
              <option value="launch">🚀 Lançamento</option><option value="community">🌍 Comunidade</option><option value="vip">⭐ VIP</option><option value="support">🛟 Suporte</option>
            </select>
            <input placeholder="Link de convite (opcional)" value={form.invite_link} onChange={e => setForm({...form, invite_link: e.target.value})} className="inp" />
            <button onClick={() => createMut.mutate(form)} disabled={!form.name || createMut.isPending}
              className="w-full py-2.5 bg-gradient-to-r from-indigo-500 to-purple-600 text-white rounded-xl text-xs font-bold shadow-lg disabled:opacity-30">
              {createMut.isPending ? 'Criando...' : 'Criar Grupo'}
            </button>
          </div>
        </Modal>
      )}

      {/* BULK CREATE MODAL */}
      {showBulk && (
        <Modal onClose={() => setShowBulk(false)} title="Criação em Massa">
          <div className="space-y-3">
            <input placeholder="Template: Grupo {n}" value={bulkForm.name_template} onChange={e => setBulkForm({...bulkForm, name_template: e.target.value})} className="inp" />
            <div className="flex gap-3">
              <input type="number" min={1} max={50} value={bulkForm.count} onChange={e => setBulkForm({...bulkForm, count: parseInt(e.target.value)})} className="inp w-24" />
              <span className="text-xs text-secondary self-center">grupos (máx 50)</span>
            </div>
            <select value={bulkForm.purpose} onChange={e => setBulkForm({...bulkForm, purpose: e.target.value})} className="inp">
              <option value="launch">🚀 Lançamento</option><option value="community">🌍 Comunidade</option><option value="vip">⭐ VIP</option>
            </select>
            <button onClick={() => bulkMut.mutate(bulkForm)} disabled={bulkMut.isPending}
              className="w-full py-2.5 bg-gradient-to-r from-amber-500 to-orange-500 text-white rounded-xl text-xs font-bold shadow-lg disabled:opacity-30">
              {bulkMut.isPending ? 'Criando...' : `Criar ${bulkForm.count} Grupos`}
            </button>
          </div>
        </Modal>
      )}

      {/* IMPORT MODAL */}
      {showImport && (
        <Modal onClose={() => setShowImport(false)} title="📥 Importar Grupos do WhatsApp">
          <div className="space-y-3">
            <p className="text-xs text-secondary">Cole os dados dos seus grupos. Um por linha no formato: <code className="bg-bg-primary px-1.5 py-0.5 rounded text-[10px]">Nome do Grupo | JID (opcional) | Link convite (opcional)</code></p>
            <textarea value={importText} onChange={e => setImportText(e.target.value)} rows={6} placeholder={"VIP Esmeralda 01 | 5511999...@g.us | https://chat.whatsapp.com/...\nVIP Esmeralda 02\nGrupo Suporte"} className="inp font-mono text-[11px]" />
            <div className="bg-bg-primary border border-border rounded-xl p-3">
              <div className="text-[10px] font-bold text-secondary mb-1">Preview: {importText.split('\n').filter(l => l.trim()).length} grupos</div>
              {importText.split('\n').filter(l => l.trim()).slice(0, 5).map((l, i) => (
                <div key={i} className="text-[10px] text-primary truncate">📥 {l.split('|')[0]?.trim()}</div>
              ))}
            </div>
            <button
              onClick={() => {
                const groups = importText.split('\n').filter(l => l.trim()).map(line => {
                  const parts = line.split('|').map(p => p.trim());
                  return { name: parts[0] || '', group_jid: parts[1] || '', invite_link: parts[2] || '' };
                }).filter(g => g.name);
                if (groups.length) importMut.mutate(groups);
              }}
              disabled={!importText.trim() || importMut.isPending}
              className="w-full py-2.5 bg-gradient-to-r from-emerald-500 to-teal-500 text-white rounded-xl text-xs font-bold shadow-lg disabled:opacity-30">
              {importMut.isPending ? 'Importando...' : `Importar ${importText.split('\n').filter(l => l.trim()).length} Grupos`}
            </button>
          </div>
        </Modal>
      )}

      {/* @TODOS MODAL */}
      {showMention !== null && (
        <Modal onClose={() => setShowMention(null)} title="📢 @todos — Menção em Massa">
          <div className="space-y-3">
            <p className="text-xs text-secondary">Envie uma mensagem mencionando todos os membros do grupo para máxima visibilidade.</p>
            <textarea value={mentionMsg} onChange={e => setMentionMsg(e.target.value)} rows={4} placeholder="Ex: 🔴 ATENÇÃO! Abertura de carrinho em 10 minutos..." className="inp" />
            <div className="bg-blue-500/5 border border-blue-500/20 rounded-xl p-3">
              <div className="text-[10px] font-bold text-blue-400 mb-1">Preview:</div>
              <div className="text-xs text-primary whitespace-pre-wrap">@todos{'\n\n'}{mentionMsg || '...'}</div>
            </div>
            <button onClick={() => mentionMut.mutate({ id: showMention, message: mentionMsg })} disabled={!mentionMsg.trim() || mentionMut.isPending}
              className="w-full py-2.5 bg-gradient-to-r from-blue-500 to-indigo-500 text-white rounded-xl text-xs font-bold shadow-lg disabled:opacity-30">
              {mentionMut.isPending ? 'Enviando...' : '📢 Enviar @todos'}
            </button>
          </div>
        </Modal>
      )}

      {/* BUTTONS MODAL */}
      {showButtons !== null && (
        <Modal onClose={() => setShowButtons(null)} title="🔘 Mensagem com Botões Interativos">
          <div className="space-y-3">
            <div className="flex gap-2">
              {(['reply_buttons', 'cta_url'] as const).map(t => (
                <button key={t} onClick={() => setBtnForm(f => ({ ...f, type: t }))}
                  className={`px-3 py-1.5 rounded-lg text-[10px] font-bold transition-all ${btnForm.type === t ? 'bg-purple-500 text-white' : 'bg-bg-primary text-secondary border border-border'}`}>
                  {t === 'reply_buttons' ? '💬 Resposta Rápida' : '🔗 Link CTA'}
                </button>
              ))}
            </div>
            <input placeholder="Cabeçalho (opcional)" value={btnForm.header} onChange={e => setBtnForm(f => ({ ...f, header: e.target.value }))} className="inp" />
            <textarea placeholder="Mensagem principal *" value={btnForm.body} onChange={e => setBtnForm(f => ({ ...f, body: e.target.value }))} rows={3} className="inp" />
            <input placeholder="Rodapé (opcional)" value={btnForm.footer} onChange={e => setBtnForm(f => ({ ...f, footer: e.target.value }))} className="inp" />

            {btnForm.type === 'reply_buttons' && (
              <div className="space-y-2">
                <div className="text-[10px] font-bold text-secondary uppercase">Botões de resposta (máx 3):</div>
                {btnForm.buttons.map((b, i) => (
                  <input key={i} placeholder={`Botão ${i + 1}: ex. Quero saber mais`} value={b.title}
                    onChange={e => { const btns = [...btnForm.buttons]; btns[i] = { ...btns[i], title: e.target.value }; setBtnForm(f => ({ ...f, buttons: btns })); }}
                    className="inp" maxLength={20} />
                ))}
                {btnForm.buttons.length < 3 && (
                  <button onClick={() => setBtnForm(f => ({ ...f, buttons: [...f.buttons, { id: `btn${f.buttons.length + 1}`, title: '' }] }))}
                    className="text-[10px] text-purple-400 font-bold">+ Adicionar botão</button>
                )}
              </div>
            )}

            {btnForm.type === 'cta_url' && (
              <div className="grid grid-cols-2 gap-2">
                <input placeholder="Texto do botão" value={btnForm.cta_text} onChange={e => setBtnForm(f => ({ ...f, cta_text: e.target.value }))} className="inp" maxLength={20} />
                <input placeholder="https://link.com" value={btnForm.cta_url} onChange={e => setBtnForm(f => ({ ...f, cta_url: e.target.value }))} className="inp" />
              </div>
            )}

            <button onClick={() => buttonMut.mutate({ id: showButtons, ...btnForm })} disabled={!btnForm.body.trim() || buttonMut.isPending}
              className="w-full py-2.5 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-xl text-xs font-bold shadow-lg disabled:opacity-30">
              {buttonMut.isPending ? 'Enviando...' : '🔘 Enviar com Botões'}
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}

function Modal({ onClose, title, children }: { onClose: () => void; title: string; children: React.ReactNode }) {
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 backdrop-blur-sm" onClick={onClose}>
      <div className="bg-bg-surface border border-border rounded-2xl p-6 w-full max-w-md shadow-2xl" onClick={e => e.stopPropagation()}>
        <h2 className="font-bold text-lg text-primary mb-4">{title}</h2>
        {children}
      </div>
    </div>
  );
}
