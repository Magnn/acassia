import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Target, Plus, Sparkles, CheckCircle2, Trash2, Star } from 'lucide-react';
import { api } from '../api/client';
import { handleApiError } from '../lib/handleApiError';
import { toast } from '../lib/toast';

const visionApi = {
  list: (category?: string) => api.get<{ items: VBItem[]; categories: string[] }>(`/saas/visionboard/${category ? `?category=${category}` : ''}`),
  create: (b: { affirmation: string; category: string; description?: string; target_date?: string }) =>
    api.post<{ ok: boolean; id: number; item: VBItem }>('/saas/visionboard/', b),
  manifest: (id: number, notes?: string) => api.put<{ ok: boolean }>(`/saas/visionboard/${id}/manifest`, { notes }),
  del: (id: number) => api.del<{ ok: boolean }>(`/saas/visionboard/${id}`),
  stats: () => api.get<{ total: number; manifested: number; pending: number; manifestation_rate: number; by_category: Record<string, number> }>('/saas/visionboard/stats'),
  generateAffirmation: (b: { category: string; intention?: string }) =>
    api.post<{ affirmation: string; visualization?: string }>('/saas/visionboard/generate-affirmation', b),
};

interface VBItem {
  id: number; category: string; affirmation: string; description: string | null;
  image_url: string | null; target_date: string | null; is_manifested: boolean;
  manifested_at: string | null; manifestation_notes: string | null; created_at: string;
}

const CATEGORIES = [
  { id: 'amor', emoji: '💕', label: 'Amor' },
  { id: 'prosperidade', emoji: '💰', label: 'Prosperidade' },
  { id: 'saude', emoji: '💚', label: 'Saúde' },
  { id: 'carreira', emoji: '🚀', label: 'Carreira' },
  { id: 'espiritual', emoji: '🔮', label: 'Espiritual' },
  { id: 'familia', emoji: '👨‍👩‍👧', label: 'Família' },
  { id: 'criatividade', emoji: '🎨', label: 'Criatividade' },
  { id: 'viagem', emoji: '✈️', label: 'Viagem' },
];

export default function VisionBoard() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [filter, setFilter] = useState('');

  const { data, isLoading } = useQuery({ queryKey: ['visionboard-list', filter], queryFn: () => visionApi.list(filter || undefined) });
  const { data: statsData } = useQuery({ queryKey: ['visionboard-stats'], queryFn: visionApi.stats });
  const items = data?.items ?? [];

  const manifestMut = useMutation({
    mutationFn: (id: number) => visionApi.manifest(id),
    onSuccess: () => { toast.success('✨ Manifestado! Parabéns!'); qc.invalidateQueries({ queryKey: ['visionboard-list'] }); qc.invalidateQueries({ queryKey: ['visionboard-stats'] }); },
    onError: handleApiError('Erro'),
  });

  const delMut = useMutation({
    mutationFn: (id: number) => visionApi.del(id),
    onSuccess: () => { toast.success('Removido'); qc.invalidateQueries({ queryKey: ['visionboard-list'] }); },
  });

  return (
    <div className="p-10 max-w-6xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-2xl bg-accent-amethyst/10 flex items-center justify-center">
              <Target className="w-5 h-5 text-accent-amethyst" />
            </div>
            <h1 className="text-3xl font-black tracking-tight">Quadro de Visão</h1>
          </div>
          <p className="text-secondary text-sm font-medium">Visualize, afirme e manifeste — acompanhe suas intenções e celebre conquistas.</p>
        </div>
        <button onClick={() => setShowCreate(true)} className="flex items-center gap-2 px-5 py-3 bg-accent-amethyst hover:bg-accent-amethyst/90 text-white rounded-2xl font-black uppercase tracking-widest text-xs transition-all">
          <Plus className="w-4 h-4" /> Nova Intenção
        </button>
      </div>

      {/* Stats */}
      {statsData && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: 'Total', value: statsData.total, icon: Target, color: 'text-accent-amethyst' },
            { label: 'Manifestados', value: statsData.manifested, icon: CheckCircle2, color: 'text-emerald-500' },
            { label: 'Em andamento', value: statsData.pending, icon: Star, color: 'text-amber-400' },
            { label: 'Taxa', value: `${statsData.manifestation_rate}%`, icon: Sparkles, color: 'text-purple-400' },
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
      )}

      {/* Category filter */}
      <div className="flex gap-2 flex-wrap">
        <button onClick={() => setFilter('')} className={`px-3 py-1.5 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all ${!filter ? 'bg-accent-amethyst text-white' : 'bg-bg-surface text-secondary'}`}>Todas</button>
        {CATEGORIES.map(c => (
          <button key={c.id} onClick={() => setFilter(c.id)} className={`px-3 py-1.5 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all ${filter === c.id ? 'bg-accent-amethyst text-white' : 'bg-bg-surface text-secondary hover:text-primary'}`}>
            {c.emoji} {c.label}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 animate-pulse">{[1,2,3].map(i => <div key={i} className="h-40 bg-bg-surface rounded-2xl" />)}</div>
      ) : items.length === 0 ? (
        <div className="bg-bg-surface border border-dashed border-border rounded-3xl p-12 text-center">
          <Target className="w-12 h-12 mx-auto text-secondary/40 mb-4" />
          <h3 className="font-black text-lg mb-2">Quadro de visão vazio</h3>
          <p className="text-secondary text-sm mb-4">Adicione suas intenções e afirmações para manifestar seus desejos.</p>
          <button onClick={() => setShowCreate(true)} className="px-5 py-3 bg-accent-amethyst text-white rounded-2xl text-xs font-black uppercase tracking-widest">Criar primeira intenção</button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {items.map(item => {
            const cat = CATEGORIES.find(c => c.id === item.category);
            return (
              <div key={item.id} className={`bg-bg-surface border rounded-2xl p-5 transition-all ${item.is_manifested ? 'border-emerald-500/30 bg-emerald-500/5' : 'border-border hover:border-accent-amethyst/30'}`}>
                <div className="flex items-start justify-between mb-3">
                  <span className="text-2xl">{cat?.emoji || '🔮'}</span>
                  <div className="flex items-center gap-1.5">
                    {item.is_manifested ? (
                      <span className="text-[9px] font-black uppercase tracking-widest bg-emerald-500/10 text-emerald-500 px-2 py-0.5 rounded-md border border-emerald-500/30">✨ Manifestado</span>
                    ) : (
                      <button onClick={() => manifestMut.mutate(item.id)} className="text-[9px] font-black uppercase tracking-widest bg-accent-amethyst/10 text-accent-amethyst px-2 py-0.5 rounded-md hover:bg-accent-amethyst/20 transition-all">Manifestar</button>
                    )}
                    <button onClick={() => delMut.mutate(item.id)} className="text-secondary hover:text-red-400"><Trash2 className="w-3.5 h-3.5" /></button>
                  </div>
                </div>
                <p className="text-sm font-bold italic mb-2">"{item.affirmation}"</p>
                {item.description && <p className="text-[11px] text-secondary mb-2">{item.description}</p>}
                <div className="flex items-center justify-between text-[10px] text-secondary">
                  <span>{cat?.label || item.category}</span>
                  {item.target_date && <span>🎯 {new Date(item.target_date + 'T12:00:00').toLocaleDateString('pt-BR')}</span>}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {showCreate && <CreateVisionModal onClose={() => setShowCreate(false)} onCreated={() => { setShowCreate(false); qc.invalidateQueries({ queryKey: ['visionboard-list'] }); qc.invalidateQueries({ queryKey: ['visionboard-stats'] }); }} />}
    </div>
  );
}

function CreateVisionModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [category, setCategory] = useState('espiritual');
  const [affirmation, setAffirmation] = useState('');
  const [description, setDescription] = useState('');
  const [targetDate, setTargetDate] = useState('');

  const genMut = useMutation({
    mutationFn: () => visionApi.generateAffirmation({ category, intention: description }),
    onSuccess: (res) => { setAffirmation(res.affirmation); if (res.visualization) setDescription(res.visualization); },
    onError: handleApiError('Erro ao gerar'),
  });

  const createMut = useMutation({
    mutationFn: () => visionApi.create({ affirmation, category, description: description || undefined, target_date: targetDate || undefined }),
    onSuccess: () => { toast.success('Intenção adicionada! ✨'); onCreated(); },
    onError: handleApiError('Erro ao criar'),
  });

  return (
    <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-6">
      <div className="bg-bg-surface border border-border rounded-3xl p-8 max-w-md w-full space-y-5">
        <h2 className="text-xl font-black tracking-tight">✨ Nova Intenção</h2>
        <F label="Categoria">
          <div className="flex flex-wrap gap-2">{CATEGORIES.map(c => (
            <button key={c.id} onClick={() => setCategory(c.id)} className={`px-3 py-2 rounded-xl text-xs font-bold transition-all ${category === c.id ? 'bg-accent-amethyst text-white' : 'bg-bg-primary text-secondary'}`}>
              {c.emoji} {c.label}
            </button>
          ))}</div>
        </F>

        <button onClick={() => genMut.mutate()} disabled={genMut.isPending}
          className="w-full text-[10px] text-accent-amethyst font-black uppercase tracking-widest hover:underline text-left">
          {genMut.isPending ? '✨ Gerando...' : '✨ Gerar afirmação com IA'}
        </button>

        <F label="Afirmação"><textarea value={affirmation} onChange={e => setAffirmation(e.target.value)} rows={2} placeholder="Eu atraio abundância ilimitada em todas as áreas da minha vida" className="inp resize-none" /></F>
        <F label="Visualização (opcional)"><textarea value={description} onChange={e => setDescription(e.target.value)} rows={2} placeholder="Me vejo em uma casa cercada de natureza, com liberdade financeira..." className="inp resize-none" /></F>
        <F label="Data-alvo (opcional)"><input type="date" value={targetDate} onChange={e => setTargetDate(e.target.value)} className="inp" /></F>
        <div className="flex gap-3">
          <button onClick={onClose} className="flex-1 px-5 py-3 bg-bg-primary border border-border rounded-2xl text-sm font-bold">Cancelar</button>
          <button onClick={() => createMut.mutate()} disabled={!affirmation || createMut.isPending}
            className="flex-1 px-5 py-3 bg-accent-amethyst hover:bg-accent-amethyst/90 disabled:opacity-30 text-white rounded-2xl text-sm font-black uppercase tracking-widest">
            {createMut.isPending ? 'Criando...' : '✨ Manifestar'}
          </button>
        </div>
      </div>
    </div>
  );
}

function F({ label, children }: { label: string; children: React.ReactNode }) {
  return <div><label className="text-[10px] uppercase font-black tracking-widest text-secondary mb-1.5 block">{label}</label>{children}</div>;
}
