import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Flame, Play, CheckCircle2, Clock, Sparkles, Moon, Heart } from 'lucide-react';
import { api } from '../api/client';
import { handleApiError } from '../lib/handleApiError';
import { toast } from '../lib/toast';

const MOODS = [
  { id: 'ansioso', emoji: '😰', label: 'Ansioso' },
  { id: 'triste', emoji: '😢', label: 'Triste' },
  { id: 'grato', emoji: '🙏', label: 'Grato' },
  { id: 'motivado', emoji: '🔥', label: 'Motivado' },
  { id: 'cansado', emoji: '😴', label: 'Cansado' },
  { id: 'confuso', emoji: '😵', label: 'Confuso' },
  { id: 'em_paz', emoji: '☮️', label: 'Em Paz' },
  { id: 'irritado', emoji: '😤', label: 'Irritado' },
];

interface Ritual {
  title: string;
  intention: string;
  steps: Array<{ order: number; type: string; duration_seconds: number; instruction: string; details?: string }>;
  mantra: string;
  recommended_color: string;
  recommended_incense: string;
  recommended_crystal: string;
  closing_message: string;
  moon_phase?: { phase_name: string; illumination_pct?: number };
  mood: string;
  sign: string;
  minutes: number;
  spiritual_date?: { name: string; description: string };
}

const ritualApi = {
  generate: (b: { mood: string; minutes_available: number; sign?: string }) =>
    api.post<{ ok: boolean; ritual: Ritual }>('/saas/ritual/generate', b),
  complete: (b: { ritual_type: string; duration_seconds: number; mood_before: string; mood_after: string; ritual_data?: unknown }) =>
    api.post<{ ok: boolean; streak_days: number; mood_shift: string }>('/saas/ritual/complete', b),
  streak: () => api.get<{ streak_days: number; monthly_rituals: number }>('/saas/ritual/streak'),
  history: (limit?: number) =>
    api.get<{ history: Array<{ id: number; ritual_type: string; duration_seconds: number; mood_before: string; mood_after: string; moon_phase: string; completed_at: string }> }>(`/saas/ritual/history?limit=${limit || 15}`),
};

export default function Rituals() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<'generate' | 'history'>('generate');
  const [mood, setMood] = useState('');
  const [minutes, setMinutes] = useState(5);
  const [generated, setGenerated] = useState<Ritual | null>(null);
  const [activeStep, setActiveStep] = useState(0);
  const [moodAfter, setMoodAfter] = useState('');

  const { data: streakData } = useQuery({ queryKey: ['ritual-streak'], queryFn: ritualApi.streak });
  const { data: histData } = useQuery({ queryKey: ['ritual-history'], queryFn: () => ritualApi.history(), enabled: tab === 'history' });

  const generateMut = useMutation({
    mutationFn: () => ritualApi.generate({ mood, minutes_available: minutes }),
    onSuccess: (res) => { setGenerated(res.ritual); setActiveStep(0); setMoodAfter(''); },
    onError: handleApiError('Erro ao gerar ritual'),
  });

  const completeMut = useMutation({
    mutationFn: () => ritualApi.complete({
      ritual_type: generated?.steps?.[0]?.type || 'general',
      duration_seconds: minutes * 60,
      mood_before: mood,
      mood_after: moodAfter,
      ritual_data: generated,
    }),
    onSuccess: (res) => {
      toast.success(`Ritual completo! 🔥 Streak: ${res.streak_days} dias`);
      setGenerated(null);
      qc.invalidateQueries({ queryKey: ['ritual-streak'] });
      qc.invalidateQueries({ queryKey: ['ritual-history'] });
    },
    onError: handleApiError('Erro ao registrar'),
  });

  return (
    <div className="p-10 max-w-4xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-2xl bg-accent-amethyst/10 flex items-center justify-center">
              <Flame className="w-5 h-5 text-accent-amethyst" />
            </div>
            <h1 className="text-3xl font-black tracking-tight">Rituais Diários</h1>
          </div>
          <p className="text-secondary text-sm font-medium">5 minutos de espiritualidade personalizada — lua + signo + humor + IA.</p>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-bg-surface border border-border rounded-2xl p-5">
          <div className="flex items-center gap-2 mb-2">
            <Flame className="w-4 h-4 text-orange-500" />
            <span className="text-[10px] font-black uppercase tracking-widest text-secondary">Streak</span>
          </div>
          <div className="text-3xl font-black tracking-tight">{streakData?.streak_days ?? 0} 🔥</div>
        </div>
        <div className="bg-bg-surface border border-border rounded-2xl p-5">
          <div className="flex items-center gap-2 mb-2">
            <Moon className="w-4 h-4 text-accent-amethyst" />
            <span className="text-[10px] font-black uppercase tracking-widest text-secondary">Este mês</span>
          </div>
          <div className="text-3xl font-black tracking-tight">{streakData?.monthly_rituals ?? 0}</div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-bg-surface border border-border rounded-2xl p-1.5 w-fit">
        {(['generate', 'history'] as const).map(t => (
          <button key={t} onClick={() => setTab(t)} className={`px-5 py-2.5 rounded-xl text-xs font-black uppercase tracking-widest transition-all ${tab === t ? 'bg-accent-amethyst text-white shadow-lg' : 'text-secondary hover:text-primary'}`}>
            {t === 'generate' ? '✨ Criar Ritual' : '📜 Histórico'}
          </button>
        ))}
      </div>

      {tab === 'generate' && !generated && (
        <div className="bg-bg-surface border border-border rounded-3xl p-8 space-y-6">
          <h3 className="text-lg font-black flex items-center gap-2"><Sparkles className="w-5 h-5 text-accent-amethyst" /> Como você está agora?</h3>
          <div className="flex flex-wrap gap-2">
            {MOODS.map(m => (
              <button key={m.id} onClick={() => setMood(m.id)}
                className={`flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-xs font-bold transition-all border ${mood === m.id ? 'bg-accent-amethyst text-white border-accent-amethyst' : 'bg-bg-primary text-secondary border-border hover:border-accent-amethyst/20'}`}>
                {m.emoji} {m.label}
              </button>
            ))}
          </div>

          <div>
            <label className="text-[10px] uppercase font-black tracking-widest text-secondary mb-2 block">Tempo disponível</label>
            <div className="flex gap-2">
              {[3, 5, 10, 15, 20].map(m => (
                <button key={m} onClick={() => setMinutes(m)}
                  className={`flex-1 px-3 py-2.5 rounded-xl text-xs font-bold transition-all ${minutes === m ? 'bg-accent-amethyst text-white' : 'bg-bg-primary text-secondary'}`}>
                  {m}min
                </button>
              ))}
            </div>
          </div>

          <button onClick={() => generateMut.mutate()} disabled={!mood || generateMut.isPending}
            className="w-full flex items-center justify-center gap-2 px-5 py-4 bg-accent-amethyst hover:bg-accent-amethyst/90 disabled:opacity-30 text-white rounded-2xl font-black uppercase tracking-widest text-sm transition-all">
            <Sparkles className="w-5 h-5" />
            {generateMut.isPending ? 'Gerando ritual...' : 'Gerar Meu Ritual'}
          </button>
        </div>
      )}

      {tab === 'generate' && generated && (
        <div className="space-y-6">
          {/* Header do ritual */}
          <div className="bg-gradient-to-br from-accent-amethyst/10 to-accent-amethyst/5 border border-accent-amethyst/20 rounded-3xl p-8 text-center">
            <h2 className="text-2xl font-black tracking-tight mb-2">{generated.title}</h2>
            <p className="text-secondary italic mb-4">"{generated.intention}"</p>
            <div className="flex justify-center gap-4 text-[11px] text-secondary">
              {generated.moon_phase && <span>🌙 {generated.moon_phase.phase_name}</span>}
              <span>⏱️ {generated.minutes}min</span>
              {generated.spiritual_date && <span>📅 {generated.spiritual_date.name}</span>}
            </div>
          </div>

          {/* Recomendações */}
          <div className="grid grid-cols-3 gap-3">
            {[
              { icon: '🕯️', label: 'Cor', value: generated.recommended_color },
              { icon: '🪔', label: 'Incenso', value: generated.recommended_incense },
              { icon: '💎', label: 'Cristal', value: generated.recommended_crystal },
            ].map(r => (
              <div key={r.label} className="bg-bg-surface border border-border rounded-2xl p-4 text-center">
                <span className="text-2xl">{r.icon}</span>
                <div className="text-[9px] font-black uppercase tracking-widest text-secondary mt-1">{r.label}</div>
                <div className="text-sm font-bold capitalize">{r.value}</div>
              </div>
            ))}
          </div>

          {/* Steps */}
          <div className="space-y-3">
            {generated.steps.map((step, i) => (
              <div key={i} onClick={() => setActiveStep(i)}
                className={`bg-bg-surface border rounded-2xl p-5 cursor-pointer transition-all ${
                  activeStep === i ? 'border-accent-amethyst/50 shadow-lg' : i < activeStep ? 'border-emerald-500/30 opacity-70' : 'border-border'
                }`}>
                <div className="flex items-center gap-3 mb-2">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-black ${
                    i < activeStep ? 'bg-emerald-500/10 text-emerald-500' : i === activeStep ? 'bg-accent-amethyst text-white' : 'bg-bg-primary text-secondary'
                  }`}>
                    {i < activeStep ? <CheckCircle2 className="w-4 h-4" /> : i + 1}
                  </div>
                  <div className="flex-1">
                    <div className="text-[9px] font-black uppercase tracking-widest text-secondary">{step.type} • {Math.round(step.duration_seconds / 60)}min</div>
                    <div className="font-bold text-sm">{step.instruction}</div>
                  </div>
                </div>
                {activeStep === i && step.details && (
                  <p className="text-[11px] text-secondary ml-11 mt-1">{step.details}</p>
                )}
              </div>
            ))}
          </div>

          {/* Mantra */}
          <div className="bg-accent-amethyst/5 border border-accent-amethyst/20 rounded-2xl p-6 text-center">
            <div className="text-[10px] font-black uppercase tracking-widest text-accent-amethyst mb-2">Mantra</div>
            <p className="text-lg font-bold italic">"{generated.mantra}"</p>
          </div>

          {/* Closing + Complete */}
          <div className="bg-bg-surface border border-border rounded-3xl p-8 space-y-4">
            <p className="text-sm text-secondary text-center italic">"{generated.closing_message}"</p>

            <div>
              <label className="text-[10px] uppercase font-black tracking-widest text-secondary mb-2 block text-center">Como se sente agora?</label>
              <div className="flex flex-wrap gap-2 justify-center">
                {MOODS.map(m => (
                  <button key={m.id} onClick={() => setMoodAfter(m.id)}
                    className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all ${moodAfter === m.id ? 'bg-emerald-500 text-white' : 'bg-bg-primary text-secondary'}`}>
                    {m.emoji} {m.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex gap-3">
              <button onClick={() => setGenerated(null)} className="flex-1 px-5 py-3 bg-bg-primary border border-border rounded-2xl text-sm font-bold">← Novo ritual</button>
              <button onClick={() => completeMut.mutate()} disabled={!moodAfter || completeMut.isPending}
                className="flex-1 px-5 py-3 bg-emerald-500 hover:bg-emerald-600 disabled:opacity-30 text-white rounded-2xl text-sm font-black uppercase tracking-widest transition-all">
                {completeMut.isPending ? 'Salvando...' : '✓ Completar Ritual'}
              </button>
            </div>
          </div>
        </div>
      )}

      {tab === 'history' && (
        <div className="space-y-3">
          {(histData?.history ?? []).length === 0 ? (
            <div className="bg-bg-surface border border-dashed border-border rounded-3xl p-12 text-center">
              <Flame className="w-12 h-12 mx-auto text-secondary/40 mb-4" />
              <h3 className="font-black text-lg mb-2">Nenhum ritual ainda</h3>
              <p className="text-secondary text-sm">Complete seu primeiro ritual para começar o tracking.</p>
            </div>
          ) : (
            (histData?.history ?? []).map(h => (
              <div key={h.id} className="bg-bg-surface border border-border rounded-2xl p-5">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-3">
                    <span className="text-xl">{MOODS.find(m => m.id === h.mood_before)?.emoji || '🔮'}</span>
                    <span className="text-secondary">→</span>
                    <span className="text-xl">{MOODS.find(m => m.id === h.mood_after)?.emoji || '✨'}</span>
                  </div>
                  <span className="text-[10px] text-secondary">{new Date(h.completed_at).toLocaleDateString('pt-BR')}</span>
                </div>
                <div className="flex items-center gap-3 text-[11px] text-secondary">
                  <span>{h.ritual_type}</span>
                  <span>🌙 {h.moon_phase}</span>
                  <span>⏱️ {Math.round((h.duration_seconds || 0) / 60)}min</span>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
