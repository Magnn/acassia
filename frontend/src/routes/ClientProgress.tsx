import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Brain, Flame, Moon, BookOpen, Target, Trophy, Send, Activity } from 'lucide-react';
import { api } from '../api/client';
import { toast } from '../lib/toast';

export default function ClientProgress() {
  const { leadId } = useParams();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [tab, setTab] = useState<'report' | 'timeline'>('report');
  const [note, setNote] = useState('');

  const { data: report, isLoading } = useQuery({
    queryKey: ['client-progress', leadId],
    queryFn: () => api.get<any>(`/saas/client-progress/${leadId}/report`),
    enabled: !!leadId,
  });

  const { data: timeline } = useQuery({
    queryKey: ['client-timeline', leadId],
    queryFn: () => api.get<any>(`/saas/client-progress/${leadId}/timeline`),
    enabled: tab === 'timeline' && !!leadId,
  });

  const noteMut = useMutation({
    mutationFn: () => api.post<any>(`/saas/client-progress/${leadId}/note`, { content: note, note_type: 'progress' }),
    onSuccess: () => { toast.success('Nota salva!'); setNote(''); },
  });

  if (isLoading) return <div className="p-10 max-w-4xl mx-auto"><div className="animate-pulse h-96 bg-bg-surface rounded-3xl" /></div>;
  if (!report) return <div className="p-10 text-center text-secondary">Cliente não encontrado.</div>;

  const s = report.summary;

  return (
    <div className="p-10 max-w-4xl mx-auto space-y-8">
      <div className="flex items-center gap-4">
        <button onClick={() => navigate(-1)} className="w-10 h-10 rounded-xl bg-bg-surface border border-border flex items-center justify-center hover:bg-bg-primary"><ArrowLeft className="w-4 h-4" /></button>
        <div>
          <h1 className="text-3xl font-black tracking-tight">Evolução do Cliente</h1>
          <p className="text-secondary text-sm">{report.lead.name}</p>
        </div>
      </div>

      {/* KPI Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { icon: '💬', label: 'Interações', value: s.readings, color: 'text-accent-amethyst' },
          { icon: '📝', label: 'Anotações', value: s.journal_entries, color: 'text-blue-400' },
          { icon: '🎯', label: 'Metas Concluídas', value: s.rituals, color: 'text-orange-400' },
          { icon: '📊', label: 'Marcos', value: s.dreams, color: 'text-purple-400' },
          { icon: '✅', label: 'Entregas', value: `${s.manifested}/${s.vision_board_items}`, color: 'text-emerald-400' },
          { icon: '🏆', label: 'Badges', value: s.badges_count, color: 'text-amber-400' },
          { icon: '⚡', label: 'Pontos / XP', value: s.total_xp, color: 'text-cyan-400' },
          { icon: '🔥', label: 'Streak Ativo', value: `${s.ritual_streak}d`, color: 'text-red-400' },
        ].map(k => (
          <div key={k.label} className="bg-bg-surface border border-border rounded-2xl p-4 text-center">
            <div className="text-2xl mb-1">{k.icon}</div>
            <div className={`text-2xl font-black ${k.color}`}>{k.value}</div>
            <div className="text-[9px] font-black uppercase text-secondary tracking-widest">{k.label}</div>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-border pb-3">
        {[
          { id: 'report' as const, icon: Brain, label: 'Relatório IA' },
          { id: 'timeline' as const, icon: Activity, label: 'Timeline' },
        ].map(t => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-black uppercase tracking-widest ${tab === t.id ? 'bg-accent-amethyst text-white' : 'bg-bg-surface text-secondary'}`}>
            <t.icon className="w-3.5 h-3.5" /> {t.label}
          </button>
        ))}
      </div>

      {tab === 'report' && (
        <div className="space-y-6">
          {/* IA Evolution Insight */}
          <div className="bg-gradient-to-br from-accent-amethyst/10 to-pink-500/5 border border-accent-amethyst/20 rounded-3xl p-6">
            <div className="flex items-center gap-2 mb-3">
              <Brain className="w-5 h-5 text-accent-amethyst" />
              <h3 className="font-black text-sm">Análise de Evolução IA</h3>
            </div>
            <p className="text-sm whitespace-pre-wrap leading-relaxed">{report.evolution_insight}</p>
          </div>

          {/* Mood Distribution */}
          {Object.keys(report.mood_30d || {}).length > 0 && (
            <div className="bg-bg-surface border border-border rounded-2xl p-6">
              <h3 className="font-black text-sm mb-4">😊 Humor (últimos 30 dias)</h3>
              <div className="flex flex-wrap gap-2">
                {Object.entries(report.mood_30d).sort(([,a]: any, [,b]: any) => b - a).map(([mood, count]: any) => (
                  <div key={mood} className="bg-bg-primary border border-border rounded-xl px-4 py-2 text-center">
                    <div className="font-bold text-sm capitalize">{mood}</div>
                    <div className="text-xs text-secondary">{count}x</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Archetypes */}
          {Object.keys(report.archetypes || {}).length > 0 && (
            <div className="bg-bg-surface border border-border rounded-2xl p-6">
              <h3 className="font-black text-sm mb-4">🌙 Arquétipos Recorrentes nos Sonhos</h3>
              <div className="flex flex-wrap gap-2">
                {Object.entries(report.archetypes).map(([arch, count]: any) => (
                  <span key={arch} className="bg-accent-amethyst/10 text-accent-amethyst px-3 py-1.5 rounded-lg text-xs font-bold">{arch} ({count}x)</span>
                ))}
              </div>
            </div>
          )}

          {/* Badges */}
          {report.badges.length > 0 && (
            <div className="bg-bg-surface border border-border rounded-2xl p-6">
              <h3 className="font-black text-sm mb-4">🏆 Conquistas</h3>
              <div className="flex flex-wrap gap-3">
                {report.badges.map((b: any, i: number) => (
                  <div key={i} className="bg-bg-primary border border-border rounded-xl px-4 py-3 flex items-center gap-2">
                    <span className="text-lg">{b.icon}</span>
                    <div><div className="font-bold text-xs">{b.name}</div><div className="text-[9px] text-secondary">{b.earned_at ? new Date(b.earned_at).toLocaleDateString('pt-BR') : ''}</div></div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Manifestation Rate */}
          {s.vision_board_items > 0 && (
            <div className="bg-bg-surface border border-border rounded-2xl p-6">
              <h3 className="font-black text-sm mb-3">🎯 Taxa de Manifestação</h3>
              <div className="flex items-center gap-4">
                <div className="flex-1 h-4 bg-bg-primary rounded-full overflow-hidden">
                  <div className="h-full bg-gradient-to-r from-accent-amethyst to-emerald-500 rounded-full transition-all" style={{ width: `${s.manifestation_rate}%` }} />
                </div>
                <span className="font-black text-lg text-emerald-400">{s.manifestation_rate}%</span>
              </div>
            </div>
          )}

          {/* Therapist Note */}
          <div className="bg-bg-surface border border-border rounded-2xl p-6">
            <h3 className="font-black text-sm mb-3">📝 Nota do Terapeuta</h3>
            <div className="flex gap-2">
              <textarea value={note} onChange={e => setNote(e.target.value)} rows={3}
                placeholder="Observações sobre o progresso deste cliente..."
                className="flex-1 bg-bg-primary border border-border rounded-xl p-3 text-sm resize-none outline-none focus:border-accent-amethyst/50" />
              <button onClick={() => noteMut.mutate()} disabled={!note.trim() || noteMut.isPending}
                className="px-4 bg-accent-amethyst disabled:opacity-30 text-white rounded-xl"><Send className="w-4 h-4" /></button>
            </div>
          </div>
        </div>
      )}

      {tab === 'timeline' && (
        <div className="space-y-3">
          {(timeline?.timeline || []).length === 0 ? (
            <div className="text-center py-16 space-y-3">
              <div className="text-5xl">📭</div>
              <h3 className="text-lg font-black">Nenhuma atividade registrada</h3>
              <p className="text-secondary text-sm">Quando o cliente usar rituais, diário ou sonhos, a timeline aparece aqui.</p>
            </div>
          ) : (timeline?.timeline || []).map((a: any, i: number) => (
            <div key={i} className="bg-bg-surface border border-border rounded-xl p-4 flex items-start gap-3">
              <span className="text-xl">{a.icon}</span>
              <div className="flex-1 min-w-0">
                <div className="font-bold text-sm">{a.title}</div>
                <div className="text-xs text-secondary truncate">{a.detail}</div>
              </div>
              <div className="text-[10px] text-secondary whitespace-nowrap">{a.at ? new Date(a.at).toLocaleDateString('pt-BR') : ''}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
