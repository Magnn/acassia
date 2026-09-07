import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { GraduationCap, Plus, Trophy, Star, Lock, CheckCircle2, Users, Zap } from 'lucide-react';
import { trailsApi, type Trail } from '../api/saas';
import { handleApiError } from '../lib/handleApiError';
import { toast } from '../lib/toast';

const CATEGORIES = [
  { id: 'tarot', label: '🃏 Tarô' },
  { id: 'meditation', label: '🧘 Meditação' },
  { id: 'astrology', label: '⭐ Astrologia' },
  { id: 'reiki', label: '✋ Reiki' },
  { id: 'spiritual', label: '🔮 Espiritual' },
  { id: 'wellbeing', label: '💚 Bem-estar' },
];

const DIFFICULTIES = [
  { id: 'beginner', label: '🌱 Iniciante', color: 'text-emerald-500' },
  { id: 'intermediate', label: '🌿 Intermediário', color: 'text-amber-400' },
  { id: 'advanced', label: '🌳 Avançado', color: 'text-red-400' },
];

export default function Trails() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<'manage' | 'catalog' | 'badges'>('manage');
  const [showCreate, setShowCreate] = useState(false);

  const { data: myData, isLoading } = useQuery({ queryKey: ['trails-mine'], queryFn: trailsApi.list });
  const { data: catalogData } = useQuery({ queryKey: ['trails-catalog'], queryFn: trailsApi.catalog, enabled: tab === 'catalog' });
  const { data: badgesData } = useQuery({ queryKey: ['trails-badges'], queryFn: trailsApi.badges, enabled: tab === 'badges' });

  const myTrails = myData?.trails ?? [];
  const catalogTrails = catalogData?.trails ?? [];
  const badges = badgesData?.badges ?? [];
  const totalXp = badgesData?.total_xp ?? 0;

  return (
    <div className="p-10 max-w-6xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-2xl bg-accent-amethyst/10 flex items-center justify-center">
              <GraduationCap className="w-5 h-5 text-accent-amethyst" />
            </div>
            <h1 className="text-3xl font-black tracking-tight">Trilhas de Aprendizado</h1>
          </div>
          <p className="text-secondary text-sm font-medium">Crie jornadas de 7, 21 ou 40 dias com XP, badges e gamificação.</p>
        </div>
        <button onClick={() => setShowCreate(true)} className="flex items-center gap-2 px-5 py-3 bg-accent-amethyst hover:bg-accent-amethyst/90 text-white rounded-2xl font-black uppercase tracking-widest text-xs transition-all">
          <Plus className="w-4 h-4" /> Nova Trilha
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-bg-surface border border-border rounded-2xl p-1.5 w-fit">
        {(['manage', 'catalog', 'badges'] as const).map(t => (
          <button key={t} onClick={() => setTab(t)} className={`px-5 py-2.5 rounded-xl text-xs font-black uppercase tracking-widest transition-all ${tab === t ? 'bg-accent-amethyst text-white shadow-lg' : 'text-secondary hover:text-primary'}`}>
            {t === 'manage' ? '📝 Minhas' : t === 'catalog' ? '🗂️ Catálogo' : '🏆 Badges'}
          </button>
        ))}
      </div>

      {tab === 'manage' && (
        isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 animate-pulse">{[1,2].map(i => <div key={i} className="h-40 bg-bg-surface rounded-2xl" />)}</div>
        ) : myTrails.length === 0 ? (
          <div className="bg-bg-surface border border-dashed border-border rounded-3xl p-12 text-center">
            <GraduationCap className="w-12 h-12 mx-auto text-secondary/40 mb-4" />
            <h3 className="font-black text-lg mb-2">Nenhuma trilha criada</h3>
            <p className="text-secondary text-sm mb-4">Crie sua primeira trilha — ex: "21 Dias de Tarot" com lições diárias e badges.</p>
            <button onClick={() => setShowCreate(true)} className="px-5 py-3 bg-accent-amethyst text-white rounded-2xl text-xs font-black uppercase tracking-widest">Criar Trilha</button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {myTrails.map(t => <TrailCard key={t.id} trail={t} onRefresh={() => qc.invalidateQueries({ queryKey: ['trails-mine'] })} />)}
          </div>
        )
      )}

      {tab === 'catalog' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {catalogTrails.length === 0 ? (
            <p className="text-secondary col-span-full text-center py-8">Nenhuma trilha publicada ainda.</p>
          ) : catalogTrails.map(t => <TrailCard key={t.id} trail={t} readonly />)}
        </div>
      )}

      {tab === 'badges' && (
        <div className="space-y-6">
          <div className="bg-bg-surface border border-border rounded-2xl p-6 text-center">
            <Zap className="w-8 h-8 text-accent-amethyst mx-auto mb-2" />
            <div className="text-4xl font-black tracking-tight">{totalXp} XP</div>
            <div className="text-[10px] text-secondary font-black uppercase tracking-widest mt-1">Experiência Total</div>
          </div>
          {badges.length === 0 ? (
            <p className="text-secondary text-center py-8">Complete trilhas para ganhar badges!</p>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {badges.map(b => (
                <div key={b.id} className="bg-bg-surface border border-accent-amethyst/20 rounded-2xl p-5 text-center group hover:border-accent-amethyst/50 transition-all">
                  <div className="text-3xl mb-2 group-hover:scale-125 transition-transform">{b.icon}</div>
                  <h4 className="font-black text-sm">{b.name}</h4>
                  <p className="text-[10px] text-secondary mt-1">{b.description}</p>
                  <div className="text-[10px] text-accent-amethyst font-bold mt-2">+{b.xp} XP</div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {showCreate && <CreateTrailModal onClose={() => setShowCreate(false)} onCreated={() => { setShowCreate(false); qc.invalidateQueries({ queryKey: ['trails-mine'] }); }} />}
    </div>
  );
}

function TrailCard({ trail: t, onRefresh, readonly }: { trail: Trail; onRefresh?: () => void; readonly?: boolean }) {
  const publishMut = useMutation({
    mutationFn: () => trailsApi.publish(t.id),
    onSuccess: () => { toast.success('Trilha publicada!'); onRefresh?.(); },
    onError: handleApiError('Erro ao publicar'),
  });

  const diff = DIFFICULTIES.find(d => d.id === t.difficulty);

  return (
    <div className="bg-bg-surface border border-border hover:border-accent-amethyst/30 rounded-2xl p-6 transition-all">
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-black text-lg">{t.title}</h3>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-[9px] font-black uppercase tracking-widest bg-accent-amethyst/10 text-accent-amethyst px-2 py-0.5 rounded-md">{t.category}</span>
            <span className={`text-[9px] font-black uppercase tracking-widest ${diff?.color || ''}`}>{diff?.label || t.difficulty}</span>
          </div>
        </div>
        {t.badge_icon && <span className="text-2xl">{t.badge_icon}</span>}
      </div>
      <p className="text-[11px] text-secondary mb-4 line-clamp-2">{t.description || 'Sem descrição'}</p>
      <div className="flex items-center gap-4 text-[11px] text-secondary mb-3">
        <span>📅 {t.duration_days} dias</span>
        <span className="flex items-center gap-1"><Zap className="w-3 h-3 text-accent-amethyst" />{t.xp_reward} XP</span>
        <span className="flex items-center gap-1"><Users className="w-3 h-3" />{t.total_enrollments} inscritos</span>
        {t.badge_name && <span className="flex items-center gap-1"><Trophy className="w-3 h-3 text-amber-400" />{t.badge_name}</span>}
      </div>
      {!readonly && (
        <div className="flex gap-2">
          <span className={`text-[9px] font-black uppercase tracking-widest px-2.5 py-1 rounded-lg border ${
            t.is_published ? 'text-emerald-500 bg-emerald-500/10 border-emerald-500/30' : 'text-amber-400 bg-amber-500/10 border-amber-500/30'
          }`}>{t.is_published ? 'Publicada' : 'Rascunho'}</span>
          {!t.is_published && (
            <button onClick={() => publishMut.mutate()} className="text-[10px] text-accent-amethyst font-black uppercase tracking-widest hover:underline">Publicar</button>
          )}
        </div>
      )}
    </div>
  );
}

function CreateTrailModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [form, setForm] = useState({ title: '', description: '', category: 'tarot', difficulty: 'beginner', duration_days: 21, xp_reward: 500, badge_name: '', badge_icon: '🏆' });
  const set = (k: string, v: unknown) => setForm(f => ({ ...f, [k]: v }));

  const createMut = useMutation({
    mutationFn: () => trailsApi.create(form),
    onSuccess: () => { toast.success('Trilha criada!'); onCreated(); },
    onError: handleApiError('Erro ao criar trilha'),
  });

  return (
    <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-6">
      <div className="bg-bg-surface border border-border rounded-3xl p-8 max-w-lg w-full space-y-4 max-h-[90vh] overflow-y-auto">
        <h2 className="text-xl font-black tracking-tight">Nova Trilha</h2>
        <F label="Título"><input value={form.title} onChange={e => set('title', e.target.value)} placeholder="21 Dias de Meditação Guiada" className="inp" /></F>
        <F label="Descrição"><textarea value={form.description} onChange={e => set('description', e.target.value)} rows={3} className="inp resize-none" /></F>
        <F label="Categoria">
          <div className="flex flex-wrap gap-2">{CATEGORIES.map(c => (
            <button key={c.id} onClick={() => set('category', c.id)} className={`px-3 py-2 rounded-xl text-xs font-bold transition-all ${form.category === c.id ? 'bg-accent-amethyst text-white' : 'bg-bg-primary text-secondary'}`}>{c.label}</button>
          ))}</div>
        </F>
        <F label="Dificuldade">
          <div className="flex gap-2">{DIFFICULTIES.map(d => (
            <button key={d.id} onClick={() => set('difficulty', d.id)} className={`flex-1 px-3 py-2 rounded-xl text-xs font-bold transition-all ${form.difficulty === d.id ? 'bg-accent-amethyst text-white' : 'bg-bg-primary text-secondary'}`}>{d.label}</button>
          ))}</div>
        </F>
        <div className="grid grid-cols-2 gap-3">
          <F label="Duração (dias)">
            <div className="flex gap-2">{[7, 14, 21, 40].map(d => (
              <button key={d} onClick={() => set('duration_days', d)} className={`flex-1 px-2 py-2 rounded-xl text-xs font-bold ${form.duration_days === d ? 'bg-accent-amethyst text-white' : 'bg-bg-primary text-secondary'}`}>{d}d</button>
            ))}</div>
          </F>
          <F label="XP de recompensa"><input type="number" value={form.xp_reward} onChange={e => set('xp_reward', +e.target.value)} className="inp" /></F>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <F label="Badge (nome)"><input value={form.badge_name} onChange={e => set('badge_name', e.target.value)} placeholder="Mestre do Tarô" className="inp" /></F>
          <F label="Badge (emoji)"><input value={form.badge_icon} onChange={e => set('badge_icon', e.target.value)} placeholder="🏆" className="inp text-2xl text-center" /></F>
        </div>
        <div className="flex gap-3 pt-2">
          <button onClick={onClose} className="flex-1 px-5 py-3 bg-bg-primary border border-border rounded-2xl text-sm font-bold">Cancelar</button>
          <button onClick={() => createMut.mutate()} disabled={!form.title || createMut.isPending} className="flex-1 px-5 py-3 bg-accent-amethyst hover:bg-accent-amethyst/90 disabled:opacity-30 text-white rounded-2xl text-sm font-black uppercase tracking-widest">
            {createMut.isPending ? 'Criando...' : 'Criar Trilha'}
          </button>
        </div>
      </div>
    </div>
  );
}

function F({ label, children }: { label: string; children: React.ReactNode }) {
  return <div><label className="text-[10px] uppercase font-black tracking-widest text-secondary mb-1.5 block">{label}</label>{children}</div>;
}
