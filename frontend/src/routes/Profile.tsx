import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Globe, Eye, Star, Plus, Trash2, ExternalLink, Copy, Palette, Save,
  Instagram, MapPin, Phone, Sparkles, CheckCircle2,
} from 'lucide-react';
import { profileApi, type Profile, type Testimonial } from '../api/saas';
import { handleApiError } from '../lib/handleApiError';
import { toast } from '../lib/toast';

const SPECIALTIES = [
  { id: 'tarot', label: '🃏 Tarô', color: 'bg-purple-500/10 text-purple-400' },
  { id: 'astrologia', label: '⭐ Astrologia', color: 'bg-blue-500/10 text-blue-400' },
  { id: 'reiki', label: '✋ Reiki', color: 'bg-emerald-500/10 text-emerald-400' },
  { id: 'terapia_floral', label: '🌸 Terapia Floral', color: 'bg-pink-500/10 text-pink-400' },
  { id: 'constelacao', label: '🌌 Constelação', color: 'bg-indigo-500/10 text-indigo-400' },
  { id: 'coaching', label: '🧠 Coaching', color: 'bg-amber-500/10 text-amber-400' },
  { id: 'meditacao', label: '🧘 Meditação', color: 'bg-teal-500/10 text-teal-400' },
  { id: 'numerologia', label: '🔢 Numerologia', color: 'bg-orange-500/10 text-orange-400' },
];

export default function ProfilePage() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<'editor' | 'testimonials'>('editor');

  const { data: profile, isLoading } = useQuery({
    queryKey: ['my-profile'],
    queryFn: profileApi.get,
  });
  const { data: statsData } = useQuery({
    queryKey: ['profile-stats'],
    queryFn: profileApi.stats,
  });

  const exists = profile?.exists;

  return (
    <div className="p-10 max-w-5xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-2xl bg-accent-amethyst/10 flex items-center justify-center">
              <Globe className="w-5 h-5 text-accent-amethyst" />
            </div>
            <h1 className="text-3xl font-black tracking-tight">Perfil Público</h1>
          </div>
          <p className="text-secondary text-sm font-medium">
            Sua landing page pública — clientes encontram e agendam por aqui.
          </p>
        </div>
        {exists && profile?.is_published && (
          <a href={profile.url} target="_blank" rel="noopener"
            className="flex items-center gap-2 px-5 py-3 bg-bg-surface border border-border hover:border-accent-amethyst/30 rounded-2xl text-xs font-black uppercase tracking-widest text-secondary hover:text-primary transition-all">
            <ExternalLink className="w-4 h-4" /> Ver Página
          </a>
        )}
      </div>

      {/* Stats */}
      {exists && (
        <div className="grid grid-cols-3 gap-4">
          {[
            { label: 'Visualizações', value: statsData?.total_views ?? 0, icon: Eye },
            { label: 'Agendamentos', value: statsData?.total_bookings ?? 0, icon: CheckCircle2 },
            { label: 'Status', value: statsData?.is_published ? '🟢 Publicado' : '🟡 Rascunho', icon: Globe },
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
      )}

      {/* Tabs */}
      <div className="flex gap-1 bg-bg-surface border border-border rounded-2xl p-1.5 w-fit">
        {(['editor', 'testimonials'] as const).map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-5 py-2.5 rounded-xl text-xs font-black uppercase tracking-widest transition-all ${
              tab === t ? 'bg-accent-amethyst text-white shadow-lg' : 'text-secondary hover:text-primary'
            }`}>
            {t === 'editor' ? '✏️ Editor' : '⭐ Depoimentos'}
          </button>
        ))}
      </div>

      {tab === 'editor' && <ProfileEditor profile={profile} isLoading={isLoading} onSaved={() => qc.invalidateQueries({ queryKey: ['my-profile'] })} />}
      {tab === 'testimonials' && <TestimonialsManager />}
    </div>
  );
}

function ProfileEditor({ profile, isLoading, onSaved }: { profile: Profile | undefined; isLoading: boolean; onSaved: () => void }) {
  const [form, setForm] = useState({
    display_name: '', headline: '', bio: '', slug: '',
    specialties: [] as string[], city: '', state: '',
    instagram: '', theme_color: '#7C3AED',
    show_services: true, show_testimonials: true, show_calendar: true,
    accept_online: true,
  });
  const [loaded, setLoaded] = useState(false);

  if (profile?.exists && !loaded) {
    setForm({
      display_name: profile.display_name || '',
      headline: profile.headline || '',
      bio: profile.bio || '',
      slug: profile.slug || '',
      specialties: profile.specialties || [],
      city: profile.city || '',
      state: profile.state || '',
      instagram: profile.instagram || '',
      theme_color: profile.theme_color || '#7C3AED',
      show_services: profile.show_services,
      show_testimonials: profile.show_testimonials,
      show_calendar: profile.show_calendar,
      accept_online: profile.accept_online,
    });
    setLoaded(true);
  }

  const saveMut = useMutation({
    mutationFn: () => profileApi.upsert(form),
    onSuccess: (res) => { toast.success(`Salvo! URL: ${res.url}`); onSaved(); },
    onError: handleApiError('Erro ao salvar perfil'),
  });

  const publishMut = useMutation({
    mutationFn: profileApi.publish,
    onSuccess: (res) => { toast.success(`Publicado em ${res.url}!`); onSaved(); },
    onError: handleApiError('Erro ao publicar'),
  });

  if (isLoading) return <div className="animate-pulse h-64 bg-bg-surface rounded-3xl" />;

  const set = (k: string, v: unknown) => setForm(f => ({ ...f, [k]: v }));

  return (
    <div className="space-y-6">
      <div className="bg-bg-surface border border-border rounded-3xl p-8 space-y-6">
        <h3 className="text-lg font-black tracking-tight flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-accent-amethyst" /> Informações
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Field label="Nome de exibição">
            <input value={form.display_name} onChange={e => set('display_name', e.target.value)} placeholder="Ana Carolina - Taróloga"
              className="w-full bg-bg-primary border border-border rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-accent-amethyst/30" />
          </Field>
          <Field label="Slug (URL)">
            <div className="flex items-center gap-2">
              <span className="text-[11px] text-secondary">/p/</span>
              <input value={form.slug} onChange={e => set('slug', e.target.value)} placeholder="ana-carolina"
                className="flex-1 bg-bg-primary border border-border rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-accent-amethyst/30" />
            </div>
          </Field>
        </div>
        <Field label="Headline">
          <input value={form.headline} onChange={e => set('headline', e.target.value)} placeholder="Taróloga & Terapeuta Holística | 10 anos de experiência"
            className="w-full bg-bg-primary border border-border rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-accent-amethyst/30" />
        </Field>
        <Field label="Bio">
          <textarea value={form.bio} onChange={e => set('bio', e.target.value)} rows={4} placeholder="Conte sobre você, sua jornada espiritual e como ajuda seus clientes..."
            className="w-full bg-bg-primary border border-border rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-accent-amethyst/30 resize-none" />
        </Field>

        <Field label="Especialidades">
          <div className="flex flex-wrap gap-2">
            {SPECIALTIES.map(s => {
              const active = form.specialties.includes(s.id);
              return (
                <button key={s.id} onClick={() => set('specialties', active ? form.specialties.filter(x => x !== s.id) : [...form.specialties, s.id])}
                  className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all border ${
                    active ? 'bg-accent-amethyst text-white border-accent-amethyst' : `${s.color} border-transparent hover:border-accent-amethyst/20`
                  }`}>
                  {s.label}
                </button>
              );
            })}
          </div>
        </Field>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Field label="Cidade">
            <input value={form.city} onChange={e => set('city', e.target.value)} placeholder="São Paulo"
              className="w-full bg-bg-primary border border-border rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-accent-amethyst/30" />
          </Field>
          <Field label="Estado">
            <input value={form.state} onChange={e => set('state', e.target.value)} placeholder="SP" maxLength={2}
              className="w-full bg-bg-primary border border-border rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-accent-amethyst/30" />
          </Field>
          <Field label="Instagram">
            <input value={form.instagram} onChange={e => set('instagram', e.target.value)} placeholder="@seuuser"
              className="w-full bg-bg-primary border border-border rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-accent-amethyst/30" />
          </Field>
          <Field label="Cor do tema">
            <input type="color" value={form.theme_color} onChange={e => set('theme_color', e.target.value)}
              className="w-full h-10 bg-bg-primary border border-border rounded-xl cursor-pointer" />
          </Field>
        </div>

        <Field label="Visibilidade na página">
          <div className="flex flex-wrap gap-3">
            {[
              { k: 'show_services', l: '📦 Serviços' },
              { k: 'show_testimonials', l: '⭐ Depoimentos' },
              { k: 'show_calendar', l: '📅 Agenda' },
              { k: 'accept_online', l: '💻 Online' },
            ].map(({ k, l }) => (
              <button key={k} onClick={() => set(k, !(form as any)[k])}
                className={`px-4 py-2 rounded-xl text-xs font-bold transition-all ${
                  (form as any)[k] ? 'bg-accent-amethyst/10 text-accent-amethyst border border-accent-amethyst/30' : 'bg-bg-primary text-secondary border border-border'
                }`}>
                {l}
              </button>
            ))}
          </div>
        </Field>
      </div>

      <div className="flex gap-3">
        <button onClick={() => saveMut.mutate()} disabled={!form.display_name || saveMut.isPending}
          className="flex-1 flex items-center justify-center gap-2 px-5 py-3.5 bg-accent-amethyst hover:bg-accent-amethyst/90 disabled:opacity-30 text-white rounded-2xl font-black uppercase tracking-widest text-xs transition-all">
          <Save className="w-4 h-4" /> {saveMut.isPending ? 'Salvando...' : 'Salvar Perfil'}
        </button>
        <button onClick={() => publishMut.mutate()} disabled={publishMut.isPending}
          className="flex items-center gap-2 px-5 py-3.5 bg-emerald-500/10 text-emerald-500 hover:bg-emerald-500/20 border border-emerald-500/30 rounded-2xl font-black uppercase tracking-widest text-xs transition-all">
          <Globe className="w-4 h-4" /> Publicar
        </button>
      </div>
    </div>
  );
}

function TestimonialsManager() {
  const qc = useQueryClient();
  const [showAdd, setShowAdd] = useState(false);
  const { data } = useQuery({ queryKey: ['profile-testimonials'], queryFn: profileApi.testimonials });
  const items = data?.testimonials ?? [];

  const delMut = useMutation({
    mutationFn: (id: number) => profileApi.deleteTestimonial(id),
    onSuccess: () => { toast.success('Removido'); qc.invalidateQueries({ queryKey: ['profile-testimonials'] }); },
  });

  return (
    <div className="space-y-4">
      <button onClick={() => setShowAdd(true)} className="flex items-center gap-2 px-5 py-3 bg-accent-amethyst hover:bg-accent-amethyst/90 text-white rounded-2xl font-black uppercase tracking-widest text-xs">
        <Plus className="w-4 h-4" /> Adicionar Depoimento
      </button>
      {items.length === 0 ? (
        <div className="bg-bg-surface border border-dashed border-border rounded-3xl p-12 text-center">
          <Star className="w-12 h-12 mx-auto text-secondary/40 mb-4" />
          <h3 className="font-black text-lg mb-2">Sem depoimentos</h3>
          <p className="text-secondary text-sm">Adicione depoimentos de clientes para sua página pública.</p>
        </div>
      ) : (
        items.map(t => (
          <div key={t.id} className="bg-bg-surface border border-border rounded-2xl p-5">
            <div className="flex items-start justify-between mb-2">
              <div>
                <div className="font-black text-sm">{t.client_name}</div>
                <div className="text-[10px] text-secondary">{t.service_type || 'Geral'} • {new Date(t.created_at).toLocaleDateString('pt-BR')}</div>
              </div>
              <div className="flex items-center gap-2">
                <div className="flex gap-0.5">{Array.from({ length: t.rating }).map((_, i) => <Star key={i} className="w-3 h-3 text-amber-400 fill-amber-400" />)}</div>
                <button onClick={() => delMut.mutate(t.id)} className="text-secondary hover:text-red-400 transition-all"><Trash2 className="w-4 h-4" /></button>
              </div>
            </div>
            <p className="text-sm text-secondary italic">"{t.text}"</p>
          </div>
        ))
      )}
      {showAdd && <AddTestimonialModal onClose={() => setShowAdd(false)} onAdded={() => { setShowAdd(false); qc.invalidateQueries({ queryKey: ['profile-testimonials'] }); }} />}
    </div>
  );
}

function AddTestimonialModal({ onClose, onAdded }: { onClose: () => void; onAdded: () => void }) {
  const [name, setName] = useState('');
  const [text, setText] = useState('');
  const [rating, setRating] = useState(5);
  const addMut = useMutation({
    mutationFn: () => profileApi.addTestimonial({ client_name: name, text, rating }),
    onSuccess: () => { toast.success('Depoimento adicionado!'); onAdded(); },
    onError: handleApiError('Erro ao adicionar'),
  });

  return (
    <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-6">
      <div className="bg-bg-surface border border-border rounded-3xl p-8 max-w-md w-full space-y-5">
        <h2 className="text-xl font-black tracking-tight">Novo Depoimento</h2>
        <Field label="Nome do cliente"><input value={name} onChange={e => setName(e.target.value)} className="w-full bg-bg-primary border border-border rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-accent-amethyst/30" /></Field>
        <Field label="Depoimento"><textarea value={text} onChange={e => setText(e.target.value)} rows={3} className="w-full bg-bg-primary border border-border rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-accent-amethyst/30 resize-none" /></Field>
        <Field label="Nota">
          <div className="flex gap-1">{[1,2,3,4,5].map(n => <button key={n} onClick={() => setRating(n)}><Star className={`w-6 h-6 transition-all ${n <= rating ? 'text-amber-400 fill-amber-400' : 'text-secondary'}`} /></button>)}</div>
        </Field>
        <div className="flex gap-3">
          <button onClick={onClose} className="flex-1 px-5 py-3 bg-bg-primary border border-border rounded-2xl text-sm font-bold">Cancelar</button>
          <button onClick={() => addMut.mutate()} disabled={!name || !text || addMut.isPending} className="flex-1 px-5 py-3 bg-accent-amethyst hover:bg-accent-amethyst/90 disabled:opacity-30 text-white rounded-2xl text-sm font-black uppercase tracking-widest">
            {addMut.isPending ? 'Salvando...' : 'Adicionar'}
          </button>
        </div>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <div><label className="text-[10px] uppercase font-black tracking-widest text-secondary mb-1.5 block">{label}</label>{children}</div>;
}
