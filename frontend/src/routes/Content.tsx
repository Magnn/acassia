import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Package, Plus, BookOpen, Headphones, FileText, Video, Eye, DollarSign } from 'lucide-react';
import { contentApi, type ContentAsset } from '../api/saas';
import { handleApiError } from '../lib/handleApiError';
import { toast } from '../lib/toast';

const ASSET_TYPES = [
  { id: 'ebook', label: '📕 E-book', icon: BookOpen },
  { id: 'meditation', label: '🧘 Meditação', icon: Headphones },
  { id: 'course', label: '🎓 Curso', icon: Video },
  { id: 'guide', label: '📄 Guia', icon: FileText },
  { id: 'audio', label: '🎵 Áudio', icon: Headphones },
];

export default function Content() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);

  const { data, isLoading } = useQuery({ queryKey: ['content-list'], queryFn: contentApi.list });
  const items = data?.assets ?? [];

  const totalRevenue = items.reduce((sum, a) => sum + (a.total_sales * a.price_cents), 0);

  return (
    <div className="p-10 max-w-6xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-2xl bg-accent-amethyst/10 flex items-center justify-center">
              <Package className="w-5 h-5 text-accent-amethyst" />
            </div>
            <h1 className="text-3xl font-black tracking-tight">Infoprodutos</h1>
          </div>
          <p className="text-secondary text-sm font-medium">Venda e-books, meditações guiadas, cursos e áudios — entrega automática via WhatsApp.</p>
        </div>
        <button onClick={() => setShowCreate(true)} className="flex items-center gap-2 px-5 py-3 bg-accent-amethyst hover:bg-accent-amethyst/90 text-white rounded-2xl font-black uppercase tracking-widest text-xs transition-all">
          <Plus className="w-4 h-4" /> Novo Produto
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: 'Produtos', value: items.length, icon: Package },
          { label: 'Vendas totais', value: items.reduce((s, a) => s + a.total_sales, 0), icon: Eye },
          { label: 'Receita', value: `R$${(totalRevenue / 100).toFixed(0)}`, icon: DollarSign },
        ].map(s => (
          <div key={s.label} className="bg-bg-surface border border-border rounded-2xl p-5">
            <div className="flex items-center gap-2 mb-2">
              <s.icon className="w-4 h-4 text-accent-amethyst" />
              <span className="text-[10px] font-black uppercase tracking-widest text-secondary">{s.label}</span>
            </div>
            <div className="text-2xl font-black tracking-tight">{s.value}</div>
          </div>
        ))}
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 animate-pulse">{[1,2,3].map(i => <div key={i} className="h-40 bg-bg-surface rounded-2xl" />)}</div>
      ) : items.length === 0 ? (
        <div className="bg-bg-surface border border-dashed border-border rounded-3xl p-12 text-center">
          <Package className="w-12 h-12 mx-auto text-secondary/40 mb-4" />
          <h3 className="font-black text-lg mb-2">Nenhum infoproduto ainda</h3>
          <p className="text-secondary text-sm mb-4">Crie seu primeiro e-book, meditação ou curso digital.</p>
          <button onClick={() => setShowCreate(true)} className="px-5 py-3 bg-accent-amethyst text-white rounded-2xl text-xs font-black uppercase tracking-widest">Criar Produto</button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {items.map(a => (
            <div key={a.id} className="bg-bg-surface border border-border hover:border-accent-amethyst/30 rounded-2xl p-5 transition-all">
              <div className="flex items-start justify-between mb-3">
                <div className="w-10 h-10 rounded-xl bg-accent-amethyst/10 flex items-center justify-center text-lg">
                  {ASSET_TYPES.find(t => t.id === a.asset_type)?.label?.substring(0, 2) || '📦'}
                </div>
                <span className={`text-[9px] font-black uppercase tracking-widest px-2 py-0.5 rounded-lg ${a.is_published ? 'bg-emerald-500/10 text-emerald-500' : 'bg-amber-500/10 text-amber-400'}`}>
                  {a.is_published ? 'Publicado' : 'Rascunho'}
                </span>
              </div>
              <h3 className="font-black text-sm mb-1">{a.title}</h3>
              <p className="text-[11px] text-secondary mb-3 line-clamp-2">{a.description || 'Sem descrição'}</p>
              <div className="flex items-center justify-between">
                <span className="text-lg font-black font-mono">R${(a.price_cents / 100).toFixed(2)}</span>
                <span className="text-[10px] text-secondary">{a.total_sales} vendas</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {showCreate && <CreateContentModal onClose={() => setShowCreate(false)} onCreated={() => { setShowCreate(false); qc.invalidateQueries({ queryKey: ['content-list'] }); }} />}
    </div>
  );
}

function CreateContentModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [form, setForm] = useState({ title: '', description: '', asset_type: 'ebook', price_cents: 4700, file_url: '' });
  const set = (k: string, v: unknown) => setForm(f => ({ ...f, [k]: v }));

  const createMut = useMutation({
    mutationFn: () => contentApi.create(form),
    onSuccess: () => { toast.success('Produto criado!'); onCreated(); },
    onError: handleApiError('Erro ao criar produto'),
  });

  return (
    <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-6">
      <div className="bg-bg-surface border border-border rounded-3xl p-8 max-w-md w-full space-y-5">
        <h2 className="text-xl font-black tracking-tight">Novo Infoproduto</h2>
        <F label="Título"><input value={form.title} onChange={e => set('title', e.target.value)} placeholder="E-book: Guia do Tarô" className="inp" /></F>
        <F label="Tipo">
          <div className="flex flex-wrap gap-2">{ASSET_TYPES.map(t => (
            <button key={t.id} onClick={() => set('asset_type', t.id)} className={`px-3 py-2 rounded-xl text-xs font-bold transition-all ${form.asset_type === t.id ? 'bg-accent-amethyst text-white' : 'bg-bg-primary text-secondary'}`}>{t.label}</button>
          ))}</div>
        </F>
        <F label="Descrição"><textarea value={form.description} onChange={e => set('description', e.target.value)} rows={3} className="inp resize-none" /></F>
        <F label="Preço (R$)"><input type="number" value={form.price_cents / 100} onChange={e => set('price_cents', Math.round(+e.target.value * 100))} step={0.01} className="inp" /></F>
        <F label="URL do arquivo"><input value={form.file_url} onChange={e => set('file_url', e.target.value)} placeholder="https://drive.google.com/..." className="inp" /></F>
        <div className="flex gap-3">
          <button onClick={onClose} className="flex-1 px-5 py-3 bg-bg-primary border border-border rounded-2xl text-sm font-bold">Cancelar</button>
          <button onClick={() => createMut.mutate()} disabled={!form.title || createMut.isPending} className="flex-1 px-5 py-3 bg-accent-amethyst hover:bg-accent-amethyst/90 disabled:opacity-30 text-white rounded-2xl text-sm font-black uppercase tracking-widest">
            {createMut.isPending ? 'Criando...' : 'Criar Produto'}
          </button>
        </div>
      </div>
    </div>
  );
}

function F({ label, children }: { label: string; children: React.ReactNode }) {
  return <div><label className="text-[10px] uppercase font-black tracking-widest text-secondary mb-1.5 block">{label}</label>{children}</div>;
}
