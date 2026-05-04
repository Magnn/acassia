import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Flame, Sparkles, Moon } from 'lucide-react';
import { api } from '../../api/client';
import { toast } from '../../lib/toast';

const MOODS = [
  { id: 'ansioso', emoji: '😰', label: 'Ansioso' }, { id: 'triste', emoji: '😢', label: 'Triste' },
  { id: 'grato', emoji: '🙏', label: 'Grato' }, { id: 'motivado', emoji: '🔥', label: 'Motivado' },
  { id: 'cansado', emoji: '😴', label: 'Cansado' }, { id: 'em_paz', emoji: '☮️', label: 'Em Paz' },
];

export default function PortalRituals() {
  const qc = useQueryClient();
  const [mood, setMood] = useState('');
  const [minutes, setMinutes] = useState(5);
  const [ritual, setRitual] = useState<any>(null);
  const [moodAfter, setMoodAfter] = useState('');

  const { data: streak } = useQuery({ queryKey: ['ritual-streak'], queryFn: () => api.get<any>('/saas/ritual/streak') });

  const genMut = useMutation({
    mutationFn: () => api.post<any>('/saas/ritual/generate', { mood, minutes_available: minutes }),
    onSuccess: (r) => { setRitual(r.ritual); setMoodAfter(''); },
  });

  const completeMut = useMutation({
    mutationFn: () => api.post<any>('/saas/ritual/complete', { ritual_type: ritual?.steps?.[0]?.type || 'general', duration_seconds: minutes * 60, mood_before: mood, mood_after: moodAfter }),
    onSuccess: (r) => { toast.success(`Ritual completo! 🔥 Streak: ${r.streak_days} dias`); setRitual(null); qc.invalidateQueries({ queryKey: ['ritual-streak'] }); },
  });

  return (
    <div className="max-w-2xl mx-auto space-y-8">
      <div className="text-center">
        <h1 className="text-3xl font-black tracking-tight mb-2">🔥 Ritual Diário</h1>
        <p className="text-zinc-400 text-sm">IA cria seu ritual personalizado com lua, signo e humor.</p>
        {streak && <div className="mt-3 text-accent-amethyst font-black text-lg">🔥 Streak: {streak.streak_days} dias</div>}
      </div>

      {!ritual ? (
        <div className="bg-zinc-900 border border-zinc-800 rounded-3xl p-8 space-y-6">
          <h3 className="font-black text-center">Como você está agora?</h3>
          <div className="flex flex-wrap gap-2 justify-center">
            {MOODS.map(m => (
              <button key={m.id} onClick={() => setMood(m.id)}
                className={`px-4 py-2.5 rounded-xl text-xs font-bold transition-all border ${mood === m.id ? 'bg-accent-amethyst text-white border-accent-amethyst' : 'border-zinc-700 text-zinc-400 hover:border-zinc-500'}`}>
                {m.emoji} {m.label}
              </button>
            ))}
          </div>
          <div className="flex gap-2 justify-center">
            {[3, 5, 10, 15].map(m => (
              <button key={m} onClick={() => setMinutes(m)}
                className={`px-4 py-2 rounded-xl text-xs font-bold ${minutes === m ? 'bg-accent-amethyst text-white' : 'bg-zinc-800 text-zinc-400'}`}>
                {m}min
              </button>
            ))}
          </div>
          <button onClick={() => genMut.mutate()} disabled={!mood || genMut.isPending}
            className="w-full py-4 bg-accent-amethyst hover:bg-accent-amethyst/90 disabled:opacity-30 text-white rounded-2xl font-black uppercase tracking-widest text-sm">
            {genMut.isPending ? '🔮 Gerando...' : '✨ Gerar Ritual'}
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="bg-gradient-to-br from-accent-amethyst/10 to-accent-amethyst/5 border border-accent-amethyst/20 rounded-3xl p-6 text-center">
            <h2 className="text-xl font-black mb-1">{ritual.title}</h2>
            <p className="text-zinc-400 italic text-sm">"{ritual.intention}"</p>
          </div>
          <div className="grid grid-cols-3 gap-2">
            {[{ i: '🕯️', l: 'Cor', v: ritual.recommended_color }, { i: '🪔', l: 'Incenso', v: ritual.recommended_incense }, { i: '💎', l: 'Cristal', v: ritual.recommended_crystal }].map(r => (
              <div key={r.l} className="bg-zinc-900 border border-zinc-800 rounded-xl p-3 text-center">
                <span className="text-lg">{r.i}</span>
                <div className="text-[9px] font-black uppercase text-zinc-500 mt-1">{r.l}</div>
                <div className="text-xs font-bold capitalize">{r.v}</div>
              </div>
            ))}
          </div>
          {ritual.steps?.map((s: any, i: number) => (
            <div key={i} className="bg-zinc-900 border border-zinc-800 rounded-2xl p-4">
              <div className="text-[9px] font-black uppercase text-zinc-500 mb-1">{s.type} • {Math.round(s.duration_seconds / 60)}min</div>
              <div className="text-sm font-bold">{s.instruction}</div>
              {s.details && <p className="text-xs text-zinc-500 mt-1">{s.details}</p>}
            </div>
          ))}
          <div className="bg-accent-amethyst/5 border border-accent-amethyst/20 rounded-xl p-4 text-center italic text-sm">"{ritual.mantra}"</div>
          <div className="flex flex-wrap gap-2 justify-center">
            {MOODS.map(m => (
              <button key={m.id} onClick={() => setMoodAfter(m.id)}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold ${moodAfter === m.id ? 'bg-emerald-500 text-white' : 'bg-zinc-800 text-zinc-500'}`}>
                {m.emoji}
              </button>
            ))}
          </div>
          <div className="flex gap-3">
            <button onClick={() => setRitual(null)} className="flex-1 py-3 bg-zinc-800 rounded-2xl font-bold text-sm">Novo</button>
            <button onClick={() => completeMut.mutate()} disabled={!moodAfter}
              className="flex-1 py-3 bg-emerald-500 disabled:opacity-30 text-white rounded-2xl font-black text-sm">✓ Completar</button>
          </div>
        </div>
      )}
    </div>
  );
}
