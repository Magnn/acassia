import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link2, Plus, Copy, Check, Trash2, BarChart3, ExternalLink, Users, Eye } from 'lucide-react';
import { api } from '../api/client';
import { toast } from '../lib/toast';

export default function SmartLinks() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [copied, setCopied] = useState('');
  const [form, setForm] = useState({ name: '', slug: '', max_per_group: 200, fb_pixel_id: '', ga_tracking_id: '', closed_title: 'Vagas Encerradas! 😢', closed_message: 'Deixe seu contato para a próxima turma!', closed_cta: 'Quero ser avisado(a)!' });

  const { data } = useQuery({
    queryKey: ['smart-links'],
    queryFn: () => api.get<{ links: any[] }>('/saas/smart/links'),
  });

  const createMut = useMutation({
    mutationFn: (d: any) => api.post('/saas/smart/links', d),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['smart-links'] }); toast.success('Smart Link criado!'); setShowCreate(false); },
  });

  const deleteMut = useMutation({
    mutationFn: (id: number) => api.delete(`/saas/smart/links/${id}`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['smart-links'] }); toast.success('Removido'); },
  });

  const copyUrl = (url: string, key: string) => {
    navigator.clipboard.writeText(url); setCopied(key); toast.success('URL copiada!');
    setTimeout(() => setCopied(''), 2000);
  };

  return (
    <div className="px-8 py-8 max-w-[1400px] mx-auto min-h-screen">
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-violet-500 to-fuchsia-600 flex items-center justify-center shadow-lg shadow-violet-500/30">
            <Link2 className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="font-display text-3xl text-primary tracking-tight">Smart Links</h1>
            <p className="text-xs text-secondary">1 link → distribui entre N grupos automaticamente</p>
          </div>
        </div>
        <button onClick={() => setShowCreate(true)} className="flex items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-violet-500 to-fuchsia-600 text-white rounded-xl text-xs font-bold shadow-lg hover:scale-105 transition-all">
          <Plus className="w-4 h-4" /> Novo Smart Link
        </button>
      </div>

      {/* Info Card */}
      <div className="bg-gradient-to-r from-violet-500/10 to-fuchsia-500/10 border border-violet-500/20 rounded-2xl p-5 mb-6">
        <h3 className="font-bold text-sm text-primary mb-1">💡 Como funciona?</h3>
        <p className="text-xs text-secondary">Crie um Smart Link, vincule aos seus grupos WA, e compartilhe um único link. O sistema distribui os leads automaticamente entre os grupos. Quando todos lotam, exibe uma página de "vagas encerradas" com formulário de reserva.</p>
      </div>

      {/* Links Grid */}
      <div className="space-y-4">
        {(data?.links || []).map((sl: any) => (
          <div key={sl.id} className="bg-bg-surface border border-border rounded-2xl p-5 hover:border-violet-500/30 transition-all group">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-fuchsia-600 flex items-center justify-center">
                  <Link2 className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h3 className="font-bold text-sm text-primary">{sl.name}</h3>
                  <div className="flex items-center gap-2 mt-0.5">
                    <code className="text-[10px] text-secondary bg-bg-sidebar px-2 py-0.5 rounded">{sl.url}</code>
                    <button onClick={() => copyUrl(sl.url, String(sl.id))} className="text-violet-400 hover:text-violet-300">
                      {copied === String(sl.id) ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                    </button>
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <a href={sl.url} target="_blank" className="text-secondary hover:text-primary"><ExternalLink className="w-4 h-4" /></a>
                <button onClick={() => deleteMut.mutate(sl.id)} className="opacity-0 group-hover:opacity-100 text-rose-400"><Trash2 className="w-4 h-4" /></button>
              </div>
            </div>
            {/* Stats */}
            <div className="grid grid-cols-4 gap-3 mt-3">
              {[
                { label: 'Cliques', value: sl.total_clicks, icon: Eye, color: 'text-blue-400' },
                { label: 'Redirecionados', value: sl.total_redirects, icon: Users, color: 'text-emerald-400' },
                { label: 'Lista Espera', value: sl.total_waitlist, icon: BarChart3, color: 'text-amber-400' },
                { label: 'Grupos', value: sl.groups_count, icon: Users, color: 'text-violet-400' },
              ].map(s => (
                <div key={s.label} className="bg-bg-sidebar rounded-xl p-3 text-center">
                  <s.icon className={`w-4 h-4 mx-auto mb-1 ${s.color}`} />
                  <div className="text-lg font-bold text-primary">{s.value}</div>
                  <div className="text-[9px] text-secondary">{s.label}</div>
                </div>
              ))}
            </div>
            {/* Pixel badges */}
            <div className="flex gap-2 mt-3">
              {sl.fb_pixel_id && <span className="text-[9px] bg-blue-500/10 text-blue-400 px-2 py-0.5 rounded font-bold">📘 FB Pixel</span>}
              {sl.ga_tracking_id && <span className="text-[9px] bg-orange-500/10 text-orange-400 px-2 py-0.5 rounded font-bold">📊 GA</span>}
              <span className="text-[9px] bg-violet-500/10 text-violet-400 px-2 py-0.5 rounded font-bold">
                Taxa: {sl.total_clicks > 0 ? Math.round(sl.total_redirects / sl.total_clicks * 100) : 0}%
              </span>
            </div>
          </div>
        ))}
        {(!data?.links?.length) && (
          <div className="text-center py-20 text-secondary">
            <Link2 className="w-12 h-12 mx-auto mb-4 opacity-30" />
            <p className="text-sm">Nenhum Smart Link criado.</p>
            <p className="text-xs mt-1">Crie um link inteligente para seus lançamentos.</p>
          </div>
        )}
      </div>

      {/* Create Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowCreate(false)}>
          <div className="bg-bg-surface border border-border rounded-2xl p-6 w-full max-w-lg max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <h2 className="font-bold text-lg text-primary mb-4">Novo Smart Link</h2>
            <div className="space-y-3">
              <div>
                <label className="text-[10px] font-bold text-secondary uppercase mb-1 block">Nome do link</label>
                <input placeholder="Ex: Lançamento VIP Maio" value={form.name} onChange={e => setForm({...form, name: e.target.value})}
                  className="w-full px-4 py-2.5 bg-bg-sidebar border border-border rounded-xl text-sm text-primary placeholder:text-secondary/50 focus:outline-none focus:border-violet-500" />
              </div>
              <div>
                <label className="text-[10px] font-bold text-secondary uppercase mb-1 block">Máx. pessoas por grupo</label>
                <input type="number" value={form.max_per_group} onChange={e => setForm({...form, max_per_group: parseInt(e.target.value)})}
                  className="w-24 px-4 py-2.5 bg-bg-sidebar border border-border rounded-xl text-sm text-primary focus:outline-none focus:border-violet-500" />
              </div>
              <hr className="border-border" />
              <h3 className="font-bold text-xs text-primary">📊 Tracking (opcional)</h3>
              <input placeholder="Facebook Pixel ID (ex: 123456789)" value={form.fb_pixel_id} onChange={e => setForm({...form, fb_pixel_id: e.target.value})}
                className="w-full px-4 py-2.5 bg-bg-sidebar border border-border rounded-xl text-sm text-primary placeholder:text-secondary/50 focus:outline-none focus:border-violet-500" />
              <input placeholder="Google Analytics ID (ex: G-XXXXXXX)" value={form.ga_tracking_id} onChange={e => setForm({...form, ga_tracking_id: e.target.value})}
                className="w-full px-4 py-2.5 bg-bg-sidebar border border-border rounded-xl text-sm text-primary placeholder:text-secondary/50 focus:outline-none focus:border-violet-500" />
              <hr className="border-border" />
              <h3 className="font-bold text-xs text-primary">🚫 Página de Vagas Encerradas</h3>
              <input placeholder="Título" value={form.closed_title} onChange={e => setForm({...form, closed_title: e.target.value})}
                className="w-full px-4 py-2.5 bg-bg-sidebar border border-border rounded-xl text-sm text-primary placeholder:text-secondary/50 focus:outline-none focus:border-violet-500" />
              <textarea placeholder="Mensagem" value={form.closed_message} onChange={e => setForm({...form, closed_message: e.target.value})} rows={2}
                className="w-full px-4 py-2.5 bg-bg-sidebar border border-border rounded-xl text-sm text-primary placeholder:text-secondary/50 focus:outline-none focus:border-violet-500 resize-none" />
              <input placeholder="Botão CTA" value={form.closed_cta} onChange={e => setForm({...form, closed_cta: e.target.value})}
                className="w-full px-4 py-2.5 bg-bg-sidebar border border-border rounded-xl text-sm text-primary placeholder:text-secondary/50 focus:outline-none focus:border-violet-500" />
              <button onClick={() => createMut.mutate(form)} disabled={!form.name || createMut.isPending}
                className="w-full py-2.5 bg-gradient-to-r from-violet-500 to-fuchsia-600 text-white rounded-xl text-xs font-bold shadow-lg mt-2">
                {createMut.isPending ? 'Criando...' : 'Criar Smart Link'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
