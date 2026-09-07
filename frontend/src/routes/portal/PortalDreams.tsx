import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Moon, Plus, Brain } from 'lucide-react';
import { api } from '../../api/client';
import { toast } from '../../lib/toast';

export default function PortalDreams() {
  const qc = useQueryClient();
  const [content, setContent] = useState('');
  const [showForm, setShowForm] = useState(false);

  const { data } = useQuery({ queryKey: ['dreams-list'], queryFn: () => api.get<any>('/saas/dreams/?limit=10') });
  const entries = data?.entries ?? [];

  const createMut = useMutation({
    mutationFn: () => api.post<any>('/saas/dreams/', { content, dream_date: new Date().toISOString().split('T')[0] }),
    onSuccess: (r) => { toast.success(`Sonho interpretado: "${r.dream.title}" 🌙`); setContent(''); setShowForm(false); qc.invalidateQueries({ queryKey: ['dreams-list'] }); },
  });

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="text-center">
        <h1 className="text-3xl font-black tracking-tight mb-2">🌙 Diário de Sonhos</h1>
        <p className="text-zinc-400 text-sm">Registre sonhos e a IA interpreta com simbologia junguiana.</p>
      </div>

      {!showForm ? (
        <button onClick={() => setShowForm(true)} className="w-full py-4 bg-accent-amethyst hover:bg-accent-amethyst/90 text-white rounded-2xl font-black uppercase tracking-widest text-sm flex items-center justify-center gap-2">
          <Plus className="w-4 h-4" /> Registrar Sonho
        </button>
      ) : (
        <div className="bg-zinc-900 border border-zinc-800 rounded-3xl p-6 space-y-4">
          <textarea value={content} onChange={e => setContent(e.target.value)} rows={5}
            placeholder="Eu estava em uma floresta escura, havia uma porta dourada..."
            className="w-full bg-zinc-800 border border-zinc-700 rounded-xl p-3 text-sm resize-none focus:border-accent-amethyst/50 outline-none" />
          <div className="flex gap-3">
            <button onClick={() => setShowForm(false)} className="flex-1 py-3 bg-zinc-800 rounded-2xl font-bold text-sm">Cancelar</button>
            <button onClick={() => createMut.mutate()} disabled={content.length < 10 || createMut.isPending}
              className="flex-1 py-3 bg-accent-amethyst disabled:opacity-30 text-white rounded-2xl font-black text-sm">
              {createMut.isPending ? '🔮 Interpretando...' : '🌙 Interpretar'}
            </button>
          </div>
        </div>
      )}

      <div className="space-y-3">
        {entries.map((e: any) => (
          <div key={e.id} className="bg-zinc-900 border border-zinc-800 rounded-2xl p-5">
            <div className="flex items-center gap-3 mb-2">
              <span className="text-xl">🌙</span>
              <div>
                <h3 className="font-black text-sm">{e.title || 'Sonho'}</h3>
                <span className="text-[10px] text-zinc-500">{e.dream_date} {e.archetype ? `• ${e.archetype}` : ''}</span>
              </div>
            </div>
            {e.symbols?.length > 0 && (
              <div className="flex flex-wrap gap-1 mb-2">
                {e.symbols.map((s: string, i: number) => <span key={i} className="text-[9px] bg-zinc-800 text-zinc-400 px-2 py-0.5 rounded">{s}</span>)}
              </div>
            )}
            <p className="text-xs text-zinc-400 line-clamp-2">{e.content}</p>
            {e.interpretation && (
              <div className="mt-3 bg-accent-amethyst/5 border border-accent-amethyst/20 rounded-xl p-3">
                <div className="text-[9px] text-accent-amethyst font-bold flex items-center gap-1 mb-1"><Brain className="w-3 h-3" /> Interpretação</div>
                <p className="text-[11px] text-zinc-400">{e.interpretation}</p>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
