import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { BookOpen, Plus, Flame, Sparkles, Heart, Trash2, Lightbulb, TrendingUp } from 'lucide-react';
import { journalApi, type JournalEntry } from '../api/saas';
import { handleApiError } from '../lib/handleApiError';
import { toast } from '../lib/toast';

const MOODS = [
  { id: 'grateful', emoji: '🙏', label: 'Gratidão' },
  { id: 'peaceful', emoji: '☮️', label: 'Paz' },
  { id: 'energized', emoji: '⚡', label: 'Energia' },
  { id: 'reflective', emoji: '🪞', label: 'Reflexivo' },
  { id: 'anxious', emoji: '😰', label: 'Ansioso' },
  { id: 'inspired', emoji: '✨', label: 'Inspirado' },
  { id: 'tired', emoji: '😴', label: 'Cansado' },
  { id: 'joyful', emoji: '😊', label: 'Alegre' },
];

export default function Journal() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);

  const { data, isLoading } = useQuery({ queryKey: ['journal-list'], queryFn: () => journalApi.list({ limit: 20 }) });
  const { data: statsData } = useQuery({ queryKey: ['journal-stats'], queryFn: journalApi.stats });
  const { data: moodsData } = useQuery({ queryKey: ['journal-moods'], queryFn: () => journalApi.moods(14) });
  const entries = data?.entries ?? [];
  const stats = statsData;

  return (
    <div className="p-10 max-w-5xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-2xl bg-accent-amethyst/10 flex items-center justify-center">
              <BookOpen className="w-5 h-5 text-accent-amethyst" />
            </div>
            <h1 className="text-3xl font-black tracking-tight">Diário de Notas</h1>
          </div>
          <p className="text-secondary text-sm font-medium">Registre insights, anotações comerciais e aprendizados — IA gera sínteses inteligentes.</p>
        </div>
        <button onClick={() => setShowCreate(true)} className="flex items-center gap-2 px-5 py-3 bg-accent-amethyst hover:bg-accent-amethyst/90 text-white rounded-2xl font-black uppercase tracking-widest text-xs transition-all">
          <Plus className="w-4 h-4" /> Nova Entrada
        </button>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Streak', value: `${stats?.current_streak ?? 0} 🔥`, icon: Flame, color: 'text-orange-500' },
          { label: 'Melhor Streak', value: stats?.best_streak ?? 0, icon: TrendingUp, color: 'text-emerald-500' },
          { label: 'Total', value: stats?.total_entries ?? 0, icon: BookOpen, color: 'text-accent-amethyst' },
          { label: 'Energia 7d', value: stats?.avg_energy_7d ? `${stats.avg_energy_7d.toFixed(1)}/10` : '—', icon: Sparkles, color: 'text-amber-400' },
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

      {/* Mood Timeline */}
      {moodsData && moodsData.moods.length > 0 && (
        <div className="bg-bg-surface border border-border rounded-2xl p-5">
          <h3 className="text-[10px] font-black uppercase tracking-widest text-secondary mb-3">Humor dos últimos 14 dias</h3>
          <div className="flex gap-1 overflow-x-auto">
            {moodsData.moods.map((m, i) => (
              <div key={i} className="flex flex-col items-center gap-1 min-w-[32px]" title={`${m.date}: ${m.mood}`}>
                <span className="text-lg">{m.emoji || '•'}</span>
                <span className="text-[8px] text-secondary">{new Date(m.date).getDate()}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Badges */}
      {stats?.badges && stats.badges.length > 0 && (
        <div className="bg-bg-surface border border-border rounded-2xl p-5">
          <h3 className="text-[10px] font-black uppercase tracking-widest text-secondary mb-3">Conquistas</h3>
          <div className="flex flex-wrap gap-2">
            {stats.badges.map((b, i) => (
              <span key={i} className="px-3 py-1.5 bg-accent-amethyst/10 text-accent-amethyst rounded-xl text-xs font-bold border border-accent-amethyst/20">
                {b.icon} {b.name}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Entries */}
      {isLoading ? (
        <div className="space-y-3 animate-pulse">{[1,2,3].map(i => <div key={i} className="h-28 bg-bg-surface rounded-2xl" />)}</div>
      ) : entries.length === 0 ? (
        <div className="bg-bg-surface border border-dashed border-border rounded-3xl p-12 text-center">
          <BookOpen className="w-12 h-12 mx-auto text-secondary/40 mb-4" />
          <h3 className="font-black text-lg mb-2">Seu diário está vazio</h3>
          <p className="text-secondary text-sm mb-4">Comece a registrar seus pensamentos e a IA gerará insights espirituais.</p>
          <button onClick={() => setShowCreate(true)} className="px-5 py-3 bg-accent-amethyst text-white rounded-2xl text-xs font-black uppercase tracking-widest">Primeira Entrada</button>
        </div>
      ) : (
        <div className="space-y-3">{entries.map(e => <EntryCard key={e.id} entry={e} onDeleted={() => qc.invalidateQueries({ queryKey: ['journal-list'] })} />)}</div>
      )}

      {showCreate && <CreateEntryModal onClose={() => setShowCreate(false)} onCreated={() => { setShowCreate(false); qc.invalidateQueries({ queryKey: ['journal-list'] }); qc.invalidateQueries({ queryKey: ['journal-stats'] }); }} />}
    </div>
  );
}

function EntryCard({ entry: e, onDeleted }: { entry: JournalEntry; onDeleted: () => void }) {
  const [expanded, setExpanded] = useState(false);
  const delMut = useMutation({ mutationFn: () => journalApi.del(e.id), onSuccess: () => { toast.success('Removida'); onDeleted(); } });

  return (
    <button onClick={() => setExpanded(!expanded)} className="w-full text-left bg-bg-surface border border-border hover:border-accent-amethyst/20 rounded-2xl p-5 transition-all">
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-3">
          <span className="text-2xl">{e.mood_emoji || '📝'}</span>
          <div>
            <h3 className="font-black text-sm">{e.title || e.entry_type}</h3>
            <span className="text-[10px] text-secondary">{new Date(e.entry_date).toLocaleDateString('pt-BR')} • Streak dia {e.streak_day}</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {e.tags?.map((t, i) => <span key={i} className="text-[9px] bg-accent-amethyst/10 text-accent-amethyst px-2 py-0.5 rounded-md font-bold">{t}</span>)}
          <button onClick={(ev) => { ev.stopPropagation(); delMut.mutate(); }} className="text-secondary hover:text-red-400"><Trash2 className="w-3.5 h-3.5" /></button>
        </div>
      </div>
      <p className={`text-sm text-secondary ${expanded ? '' : 'line-clamp-2'}`}>{e.content}</p>
      {expanded && e.ai_insight && (
        <div className="mt-3 bg-accent-amethyst/5 border border-accent-amethyst/20 rounded-xl p-3">
          <div className="flex items-center gap-1 text-[10px] text-accent-amethyst font-black uppercase tracking-widest mb-1"><Lightbulb className="w-3 h-3" /> Insight IA</div>
          <p className="text-[11px] text-secondary">{e.ai_insight}</p>
        </div>
      )}
    </button>
  );
}

function CreateEntryModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [content, setContent] = useState('');
  const [mood, setMood] = useState('');
  const [energy, setEnergy] = useState(7);
  const [title, setTitle] = useState('');
  const [prompt, setPrompt] = useState('');

  const promptMut = useMutation({
    mutationFn: () => journalApi.prompt({ mood: mood || undefined }),
    onSuccess: (res) => setPrompt(res.prompt),
  });

  const createMut = useMutation({
    mutationFn: () => journalApi.create({ content, mood: mood || undefined, energy_level: energy, title: title || undefined, generate_insight: true }),
    onSuccess: (res) => {
      const msg = res.badges_earned?.length ? `Salvo! 🎉 Badge: ${res.badges_earned[0].name}` : `Salvo! Streak: ${res.streak} dias 🔥`;
      toast.success(msg);
      onCreated();
    },
    onError: handleApiError('Erro ao salvar'),
  });

  return (
    <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-6">
      <div className="bg-bg-surface border border-border rounded-3xl p-8 max-w-lg w-full space-y-5 max-h-[90vh] overflow-y-auto">
        <h2 className="text-xl font-black tracking-tight">Nova Entrada</h2>

        <F label="Como você está?">
          <div className="flex flex-wrap gap-2">
            {MOODS.map(m => (
              <button key={m.id} onClick={() => setMood(m.id)} className={`flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-bold transition-all ${mood === m.id ? 'bg-accent-amethyst text-white' : 'bg-bg-primary text-secondary hover:text-primary'}`}>
                {m.emoji} {m.label}
              </button>
            ))}
          </div>
        </F>

        <F label={`Energia: ${energy}/10`}>
          <input type="range" min={1} max={10} value={energy} onChange={e => setEnergy(+e.target.value)} className="w-full accent-accent-amethyst" />
        </F>

        {prompt && <div className="bg-accent-amethyst/5 border border-accent-amethyst/20 rounded-xl p-3 text-sm text-secondary italic">{prompt}</div>}
        <button onClick={() => promptMut.mutate()} className="text-[10px] text-accent-amethyst font-black uppercase tracking-widest hover:underline">
          ✨ Gerar prompt guiado
        </button>

        <F label="Título (opcional)"><input value={title} onChange={e => setTitle(e.target.value)} placeholder="Reflexão da manhã..." className="inp" /></F>
        <F label="Seus pensamentos">
          <textarea value={content} onChange={e => setContent(e.target.value)} rows={5} placeholder="Escreva o que está sentindo, sonhos, rituais, insights..." className="inp resize-none" />
        </F>

        <div className="flex gap-3">
          <button onClick={onClose} className="flex-1 px-5 py-3 bg-bg-primary border border-border rounded-2xl text-sm font-bold">Cancelar</button>
          <button onClick={() => createMut.mutate()} disabled={!content || createMut.isPending} className="flex-1 px-5 py-3 bg-accent-amethyst hover:bg-accent-amethyst/90 disabled:opacity-30 text-white rounded-2xl text-sm font-black uppercase tracking-widest">
            {createMut.isPending ? 'Salvando...' : '📝 Salvar'}
          </button>
        </div>
      </div>
    </div>
  );
}

function F({ label, children }: { label: string; children: React.ReactNode }) {
  return <div><label className="text-[10px] uppercase font-black tracking-widest text-secondary mb-1.5 block">{label}</label>{children}</div>;
}
