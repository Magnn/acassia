import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { BookOpen, Sparkles, Send } from 'lucide-react';
import { api } from '../../api/client';
import { toast } from '../../lib/toast';

const MOODS = [
  { id: 'ansioso', emoji: '😰' }, { id: 'grato', emoji: '🙏' }, { id: 'motivado', emoji: '🔥' },
  { id: 'triste', emoji: '😢' }, { id: 'calmo', emoji: '😌' }, { id: 'introspectivo', emoji: '🔮' },
  { id: 'energizado', emoji: '⚡' }, { id: 'amoroso', emoji: '💜' },
];

const TYPES = [
  { id: 'free', label: '✍️ Livre' }, { id: 'gratitude', label: '🙏 Gratidão' },
  { id: 'intention', label: '🎯 Intenção' }, { id: 'reflection', label: '🪞 Reflexão' },
  { id: 'shadow_work', label: '🌑 Sombra' }, { id: 'affirmation', label: '✨ Afirmação' },
  { id: 'moon_ritual', label: '🌙 Lua' },
];

export default function PortalJournal() {
  const qc = useQueryClient();
  const [content, setContent] = useState('');
  const [mood, setMood] = useState('');
  const [entryType, setEntryType] = useState('free');
  const [prompt, setPrompt] = useState('');

  const { data } = useQuery({ queryKey: ['journal-entries'], queryFn: () => api.get<any>('/saas/journal/?limit=10') });
  const { data: stats } = useQuery({ queryKey: ['journal-stats'], queryFn: () => api.get<any>('/saas/journal/stats') });
  const entries = data?.entries ?? [];

  const promptMut = useMutation({
    mutationFn: () => api.post<any>('/saas/journal/prompt', { entry_type: entryType, mood }),
    onSuccess: (r) => { setPrompt(r.prompt); },
  });

  const createMut = useMutation({
    mutationFn: () => api.post<any>('/saas/journal/', { content, entry_type: entryType, mood, generate_insight: true }),
    onSuccess: (r) => {
      let msg = `📔 Salvo! Streak: ${r.streak} dias`;
      if (r.badges_earned?.length) msg += ` 🏆 ${r.badges_earned[0].name}!`;
      toast.success(msg);
      setContent(''); setMood(''); setPrompt('');
      qc.invalidateQueries({ queryKey: ['journal-entries'] });
      qc.invalidateQueries({ queryKey: ['journal-stats'] });
    },
  });

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="text-center">
        <h1 className="text-3xl font-black tracking-tight mb-2">📔 Diário Espiritual</h1>
        <p className="text-zinc-400 text-sm">Escreva, reflita e receba insights da IA.</p>
      </div>

      {stats && (
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 text-center">
            <div className="text-2xl font-black text-accent-amethyst">{stats.current_streak}</div>
            <div className="text-[9px] font-bold uppercase text-zinc-500">Streak</div>
          </div>
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 text-center">
            <div className="text-2xl font-black">{stats.total_entries}</div>
            <div className="text-[9px] font-bold uppercase text-zinc-500">Entradas</div>
          </div>
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 text-center">
            <div className="text-2xl font-black text-amber-400">{stats.best_streak}</div>
            <div className="text-[9px] font-bold uppercase text-zinc-500">Melhor</div>
          </div>
        </div>
      )}

      <div className="bg-zinc-900 border border-zinc-800 rounded-3xl p-6 space-y-4">
        <div className="flex flex-wrap gap-1.5">
          {TYPES.map(t => (
            <button key={t.id} onClick={() => setEntryType(t.id)}
              className={`px-3 py-1.5 rounded-lg text-[10px] font-bold ${entryType === t.id ? 'bg-accent-amethyst text-white' : 'bg-zinc-800 text-zinc-400'}`}>
              {t.label}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap gap-1.5">
          {MOODS.map(m => (
            <button key={m.id} onClick={() => setMood(m.id)}
              className={`w-9 h-9 rounded-lg text-lg ${mood === m.id ? 'bg-accent-amethyst ring-2 ring-accent-amethyst/50' : 'bg-zinc-800 hover:bg-zinc-700'}`}>
              {m.emoji}
            </button>
          ))}
        </div>
        <button onClick={() => promptMut.mutate()} className="text-[10px] text-accent-amethyst font-bold underline">✨ Gerar prompt guiado</button>
        {prompt && <div className="bg-accent-amethyst/5 border border-accent-amethyst/20 rounded-xl p-3 text-xs italic">{prompt}</div>}
        <textarea value={content} onChange={e => setContent(e.target.value)} rows={5}
          placeholder="Escreva livremente..."
          className="w-full bg-zinc-800 border border-zinc-700 rounded-xl p-3 text-sm resize-none outline-none focus:border-accent-amethyst/50" />
        <button onClick={() => createMut.mutate()} disabled={content.length < 10 || createMut.isPending}
          className="w-full py-3 bg-accent-amethyst disabled:opacity-30 text-white rounded-2xl font-black uppercase tracking-widest text-sm">
          {createMut.isPending ? 'Salvando...' : '📔 Salvar & Receber Insight IA'}
        </button>
      </div>

      <div className="space-y-3">
        {entries.map((e: any) => (
          <div key={e.id} className="bg-zinc-900 border border-zinc-800 rounded-2xl p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] text-zinc-500">{e.entry_date} • {e.entry_type} {e.mood_emoji}</span>
              <span className="text-[10px] text-accent-amethyst">🔥 {e.streak_day}d</span>
            </div>
            <p className="text-xs text-zinc-400 line-clamp-3">{e.content}</p>
            {e.ai_insight && (
              <div className="mt-2 bg-accent-amethyst/5 border border-accent-amethyst/20 rounded-xl p-3">
                <p className="text-[11px] text-zinc-400 italic">🔮 {e.ai_insight}</p>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
