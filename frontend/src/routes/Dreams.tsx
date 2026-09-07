import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Moon, Plus, Brain, Sparkles, Trash2, Eye, BarChart3 } from 'lucide-react';
import { api } from '../api/client';
import { handleApiError } from '../lib/handleApiError';
import { toast } from '../lib/toast';

const dreamsApi = {
  list: (p?: { limit?: number; page?: number }) =>
    api.get<{ entries: DreamEntry[]; total: number; page: number; pages: number }>(`/saas/dreams/?limit=${p?.limit || 20}&page=${p?.page || 1}`),
  create: (b: { content: string; dream_date?: string; lucidity_level?: number }) =>
    api.post<{ ok: boolean; id: number; dream: DreamEntry }>('/saas/dreams/', b),
  del: (id: number) => api.del<{ ok: boolean }>(`/saas/dreams/${id}`),
  patterns: () => api.get<{ total_dreams: number; top_symbols: [string, number][]; top_archetypes: [string, number][]; emotional_tones: [string, number][] }>('/saas/dreams/patterns'),
};

interface DreamEntry {
  id: number; content: string; title: string | null; dream_date: string | null;
  symbols: string[]; interpretation: string | null; emotional_tone: string | null;
  archetype: string | null; recurring_themes: string[]; lucidity_level: number | null;
  moon_phase: string | null; sign: string | null; created_at: string;
}

const ARCHETYPES: Record<string, { emoji: string; label: string }> = {
  sombra: { emoji: '🌑', label: 'Sombra' }, anima: { emoji: '🌊', label: 'Anima' },
  animus: { emoji: '⚡', label: 'Animus' }, self: { emoji: '☀️', label: 'Self' },
  trickster: { emoji: '🃏', label: 'Trickster' }, grande_mae: { emoji: '🌿', label: 'Grande Mãe' },
  velho_sabio: { emoji: '🧙', label: 'Velho Sábio' }, heroi: { emoji: '🗡️', label: 'Herói' },
  crianca_divina: { emoji: '👶', label: 'Criança Divina' },
};

export default function Dreams() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<'dreams' | 'patterns'>('dreams');
  const [showCreate, setShowCreate] = useState(false);
  const [expanded, setExpanded] = useState<number | null>(null);

  const { data, isLoading } = useQuery({ queryKey: ['dreams-list'], queryFn: () => dreamsApi.list() });
  const { data: patternsData } = useQuery({ queryKey: ['dreams-patterns'], queryFn: dreamsApi.patterns, enabled: tab === 'patterns' });
  const entries = data?.entries ?? [];

  const delMut = useMutation({
    mutationFn: (id: number) => dreamsApi.del(id),
    onSuccess: () => { toast.success('Sonho removido'); qc.invalidateQueries({ queryKey: ['dreams-list'] }); },
  });

  return (
    <div className="p-10 max-w-5xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-2xl bg-accent-amethyst/10 flex items-center justify-center">
              <Moon className="w-5 h-5 text-accent-amethyst" />
            </div>
            <h1 className="text-3xl font-black tracking-tight">Interpretador de Sonhos</h1>
          </div>
          <p className="text-secondary text-sm font-medium">Registre sonhos e a IA interpreta com simbologia junguiana, arquétipos e conexões espirituais.</p>
        </div>
        <button onClick={() => setShowCreate(true)} className="flex items-center gap-2 px-5 py-3 bg-accent-amethyst hover:bg-accent-amethyst/90 text-white rounded-2xl font-black uppercase tracking-widest text-xs transition-all">
          <Plus className="w-4 h-4" /> Registrar Sonho
        </button>
      </div>

      <div className="flex gap-1 bg-bg-surface border border-border rounded-2xl p-1.5 w-fit">
        {(['dreams', 'patterns'] as const).map(t => (
          <button key={t} onClick={() => setTab(t)} className={`px-5 py-2.5 rounded-xl text-xs font-black uppercase tracking-widest transition-all ${tab === t ? 'bg-accent-amethyst text-white shadow-lg' : 'text-secondary hover:text-primary'}`}>
            {t === 'dreams' ? '🌙 Sonhos' : '🧠 Padrões'}
          </button>
        ))}
      </div>

      {tab === 'dreams' && (
        isLoading ? (
          <div className="space-y-3 animate-pulse">{[1,2,3].map(i => <div key={i} className="h-28 bg-bg-surface rounded-2xl" />)}</div>
        ) : entries.length === 0 ? (
          <div className="bg-bg-surface border border-dashed border-border rounded-3xl p-12 text-center">
            <Moon className="w-12 h-12 mx-auto text-secondary/40 mb-4" />
            <h3 className="font-black text-lg mb-2">Nenhum sonho registrado</h3>
            <p className="text-secondary text-sm mb-4">Registre seu primeiro sonho e a IA vai interpretá-lo com simbologia profunda.</p>
            <button onClick={() => setShowCreate(true)} className="px-5 py-3 bg-accent-amethyst text-white rounded-2xl text-xs font-black uppercase tracking-widest">Registrar Sonho</button>
          </div>
        ) : (
          <div className="space-y-3">
            {entries.map(e => (
              <div key={e.id} onClick={() => setExpanded(expanded === e.id ? null : e.id)}
                className="bg-bg-surface border border-border hover:border-accent-amethyst/20 rounded-2xl p-5 cursor-pointer transition-all">
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">{ARCHETYPES[e.archetype || '']?.emoji || '🌙'}</span>
                    <div>
                      <h3 className="font-black text-sm">{e.title || 'Sonho sem título'}</h3>
                      <span className="text-[10px] text-secondary">{e.dream_date ? new Date(e.dream_date + 'T12:00:00').toLocaleDateString('pt-BR') : '—'} {e.moon_phase ? `• 🌙 ${e.moon_phase}` : ''}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {e.emotional_tone && <span className="text-[9px] font-black uppercase tracking-widest bg-accent-amethyst/10 text-accent-amethyst px-2 py-0.5 rounded-md">{e.emotional_tone}</span>}
                    <button onClick={(ev) => { ev.stopPropagation(); delMut.mutate(e.id); }} className="text-secondary hover:text-red-400"><Trash2 className="w-3.5 h-3.5" /></button>
                  </div>
                </div>
                {e.symbols?.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mb-2">
                    {e.symbols.map((s, i) => <span key={i} className="text-[9px] bg-bg-primary text-secondary px-2 py-0.5 rounded-md border border-border">{s}</span>)}
                  </div>
                )}
                <p className={`text-sm text-secondary ${expanded === e.id ? '' : 'line-clamp-2'}`}>{e.content}</p>
                {expanded === e.id && e.interpretation && (
                  <div className="mt-4 bg-accent-amethyst/5 border border-accent-amethyst/20 rounded-xl p-4">
                    <div className="flex items-center gap-1 text-[10px] text-accent-amethyst font-black uppercase tracking-widest mb-2"><Brain className="w-3 h-3" /> Interpretação</div>
                    <p className="text-[12px] text-secondary leading-relaxed">{e.interpretation}</p>
                    {e.archetype && (
                      <div className="mt-3 text-[11px] text-secondary">
                        <strong>Arquétipo:</strong> {ARCHETYPES[e.archetype]?.emoji} {ARCHETYPES[e.archetype]?.label || e.archetype}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )
      )}

      {tab === 'patterns' && patternsData && (
        <div className="space-y-6">
          <div className="bg-bg-surface border border-border rounded-2xl p-6 text-center">
            <div className="text-4xl font-black tracking-tight">{patternsData.total_dreams}</div>
            <div className="text-[10px] font-black uppercase tracking-widest text-secondary">Sonhos Analisados</div>
          </div>
          {patternsData.top_symbols.length > 0 && (
            <div className="bg-bg-surface border border-border rounded-2xl p-6">
              <h3 className="text-[10px] font-black uppercase tracking-widest text-secondary mb-3">Símbolos mais frequentes</h3>
              <div className="flex flex-wrap gap-2">
                {patternsData.top_symbols.map(([sym, count]) => (
                  <span key={sym} className="px-3 py-1.5 bg-accent-amethyst/10 text-accent-amethyst rounded-xl text-xs font-bold border border-accent-amethyst/20">
                    {sym} <span className="opacity-60">×{count}</span>
                  </span>
                ))}
              </div>
            </div>
          )}
          {patternsData.top_archetypes.length > 0 && (
            <div className="bg-bg-surface border border-border rounded-2xl p-6">
              <h3 className="text-[10px] font-black uppercase tracking-widest text-secondary mb-3">Arquétipos dominantes</h3>
              <div className="flex flex-wrap gap-3">
                {patternsData.top_archetypes.map(([arch, count]) => (
                  <div key={arch} className="text-center">
                    <div className="text-2xl">{ARCHETYPES[arch]?.emoji || '🔮'}</div>
                    <div className="text-xs font-bold">{ARCHETYPES[arch]?.label || arch}</div>
                    <div className="text-[10px] text-secondary">×{count}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {showCreate && <CreateDreamModal onClose={() => setShowCreate(false)} onCreated={() => { setShowCreate(false); qc.invalidateQueries({ queryKey: ['dreams-list'] }); }} />}
    </div>
  );
}

function CreateDreamModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [content, setContent] = useState('');
  const [dreamDate, setDreamDate] = useState(new Date().toISOString().split('T')[0]);
  const [lucidity, setLucidity] = useState(1);

  const createMut = useMutation({
    mutationFn: () => dreamsApi.create({ content, dream_date: dreamDate, lucidity_level: lucidity }),
    onSuccess: (res) => {
      toast.success(`Sonho interpretado: "${res.dream.title}" 🌙`);
      onCreated();
    },
    onError: handleApiError('Erro ao interpretar'),
  });

  return (
    <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-6">
      <div className="bg-bg-surface border border-border rounded-3xl p-8 max-w-lg w-full space-y-5 max-h-[90vh] overflow-y-auto">
        <h2 className="text-xl font-black tracking-tight">🌙 Registrar Sonho</h2>
        <F label="Data do sonho"><input type="date" value={dreamDate} onChange={e => setDreamDate(e.target.value)} className="inp" /></F>
        <F label="Descreva seu sonho">
          <textarea value={content} onChange={e => setContent(e.target.value)} rows={6} placeholder="Eu estava em uma floresta escura, havia uma porta dourada ao fundo..." className="inp resize-none" />
          <div className="text-[10px] text-secondary mt-1">Quanto mais detalhes, mais precisa a interpretação.</div>
        </F>
        <F label={`Lucidez: ${lucidity}/5`}>
          <input type="range" min={1} max={5} value={lucidity} onChange={e => setLucidity(+e.target.value)} className="w-full accent-accent-amethyst" />
          <div className="flex justify-between text-[9px] text-secondary"><span>Confuso</span><span>Muito lúcido</span></div>
        </F>
        <div className="flex gap-3">
          <button onClick={onClose} className="flex-1 px-5 py-3 bg-bg-primary border border-border rounded-2xl text-sm font-bold">Cancelar</button>
          <button onClick={() => createMut.mutate()} disabled={content.length < 10 || createMut.isPending}
            className="flex-1 px-5 py-3 bg-accent-amethyst hover:bg-accent-amethyst/90 disabled:opacity-30 text-white rounded-2xl text-sm font-black uppercase tracking-widest">
            {createMut.isPending ? '🔮 Interpretando...' : '🌙 Interpretar'}
          </button>
        </div>
      </div>
    </div>
  );
}

function F({ label, children }: { label: string; children: React.ReactNode }) {
  return <div><label className="text-[10px] uppercase font-black tracking-widest text-secondary mb-1.5 block">{label}</label>{children}</div>;
}
