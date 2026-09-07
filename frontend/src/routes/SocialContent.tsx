import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { Megaphone, Calendar, Copy, Download, Sparkles, FileText, Video, ImageIcon, Mail } from 'lucide-react';
import { api } from '../api/client';
import { handleApiError } from '../lib/handleApiError';
import { toast } from '../lib/toast';

const socialApi = {
  post: (b: any) => api.post<{ ok: boolean; content: any }>('/saas/social/generate-post', b),
  reel: (b: any) => api.post<{ ok: boolean; content: any }>('/saas/social/generate-reel', b),
  story: (b: any) => api.post<{ ok: boolean; content: any }>('/saas/social/generate-story', b),
  newsletter: (b: any) => api.post<{ ok: boolean; content: any }>('/saas/social/generate-newsletter', b),
  calendar: (niche?: string) => api.get<{ calendar: any }>(`/saas/social/calendar?niche=${niche || 'tarot'}`),
  history: () => api.get<{ history: any[] }>('/saas/social/history'),
};

const NICHES = [
  { id: 'tarot', label: '🔮 Tarot' }, { id: 'astrologia', label: '⭐ Astrologia' },
  { id: 'terapia_holistica', label: '🧘 Holístico' }, { id: 'meditacao', label: '🕯️ Meditação' },
  { id: 'cristais', label: '💎 Cristais' }, { id: 'numerologia', label: '🔢 Numerologia' },
];

const TYPES = [
  { id: 'post', icon: FileText, label: 'Post', fn: 'post' as const },
  { id: 'reel', icon: Video, label: 'Reel/TikTok', fn: 'reel' as const },
  { id: 'story', icon: ImageIcon, label: 'Stories', fn: 'story' as const },
  { id: 'newsletter', icon: Mail, label: 'Newsletter', fn: 'newsletter' as const },
];

export default function SocialContent() {
  const [tab, setTab] = useState<'generate' | 'calendar' | 'history'>('generate');
  const [contentType, setContentType] = useState('post');
  const [niche, setNiche] = useState('tarot');
  const [topic, setTopic] = useState('');
  const [result, setResult] = useState<any>(null);

  const genMut = useMutation({
    mutationFn: () => {
      const body = { topic, niche };
      const fn = socialApi[contentType as keyof typeof socialApi];
      return (fn as any)(body);
    },
    onSuccess: (r: any) => { setResult(r.content); toast.success('Conteúdo gerado!'); },
    onError: handleApiError('Erro'),
  });

  const copyAll = () => {
    const text = JSON.stringify(result, null, 2);
    navigator.clipboard.writeText(result?.caption || result?.script?.map((s: any) => s.text).join('\n') || text);
    toast.success('Copiado!');
  };

  return (
    <div className="p-10 max-w-4xl mx-auto space-y-8">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-pink-500 to-orange-500 flex items-center justify-center">
          <Megaphone className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="text-3xl font-black tracking-tight">Gerador de Conteúdo</h1>
          <p className="text-secondary text-sm">IA cria posts, reels, stories e newsletters para você.</p>
        </div>
      </div>

      <div className="flex gap-2 border-b border-border pb-3">
        {[{ id: 'generate' as const, icon: Sparkles, label: 'Gerar' }, { id: 'calendar' as const, icon: Calendar, label: 'Calendário' }].map(t => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-black uppercase tracking-widest ${tab === t.id ? 'bg-accent-amethyst text-white' : 'bg-bg-surface text-secondary'}`}>
            <t.icon className="w-3.5 h-3.5" /> {t.label}
          </button>
        ))}
      </div>

      {tab === 'generate' && (
        <div className="space-y-6">
          {!result ? (
            <div className="bg-bg-surface border border-border rounded-3xl p-8 space-y-5">
              <F label="Tipo de Conteúdo">
                <div className="grid grid-cols-4 gap-2">
                  {TYPES.map(t => (
                    <button key={t.id} onClick={() => setContentType(t.id)}
                      className={`flex flex-col items-center gap-1 p-3 rounded-xl border text-xs font-bold transition-all ${contentType === t.id ? 'border-accent-amethyst bg-accent-amethyst/10 text-accent-amethyst' : 'border-border text-secondary hover:border-border/80'}`}>
                      <t.icon className="w-5 h-5" />{t.label}
                    </button>
                  ))}
                </div>
              </F>
              <F label="Seu nicho">
                <div className="flex flex-wrap gap-2">
                  {NICHES.map(n => (
                    <button key={n.id} onClick={() => setNiche(n.id)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-bold ${niche === n.id ? 'bg-accent-amethyst text-white' : 'bg-bg-primary text-secondary'}`}>
                      {n.label}
                    </button>
                  ))}
                </div>
              </F>
              <F label="Tema (opcional)">
                <input value={topic} onChange={e => setTopic(e.target.value)} placeholder="Ex: carta da semana, lua cheia, dica de cristal..." className="inp" />
              </F>
              <button onClick={() => genMut.mutate()} disabled={genMut.isPending}
                className="w-full py-4 bg-gradient-to-r from-pink-500 to-orange-500 hover:opacity-90 disabled:opacity-30 text-white rounded-2xl font-black uppercase tracking-widest text-sm">
                {genMut.isPending ? '✨ Gerando...' : `Gerar ${TYPES.find(t => t.id === contentType)?.label}`}
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <h3 className="font-black">{result.title || 'Conteúdo Gerado'}</h3>
                <div className="flex gap-2">
                  <button onClick={copyAll} className="flex items-center gap-1 px-3 py-1.5 bg-bg-surface border border-border rounded-lg text-xs font-bold"><Copy className="w-3 h-3" /> Copiar</button>
                  <button onClick={() => setResult(null)} className="px-3 py-1.5 bg-accent-amethyst text-white rounded-lg text-xs font-bold">Novo</button>
                </div>
              </div>
              {result.hook && <div className="bg-accent-amethyst/10 border border-accent-amethyst/20 rounded-xl p-4"><span className="text-[9px] font-black uppercase text-accent-amethyst">Hook</span><p className="text-sm font-bold mt-1">{result.hook}</p></div>}
              {result.caption && <div className="bg-bg-surface border border-border rounded-2xl p-5"><span className="text-[9px] font-black uppercase text-secondary">Legenda</span><p className="text-sm whitespace-pre-wrap mt-2">{result.caption}</p></div>}
              {result.script && (
                <div className="space-y-2">{result.script.map((s: any, i: number) => (
                  <div key={i} className="bg-bg-surface border border-border rounded-xl p-4">
                    <span className="text-[9px] font-black uppercase text-accent-amethyst">{s.timestamp}</span>
                    <p className="text-sm font-bold mt-1">{s.text}</p>
                    {s.visual && <p className="text-[11px] text-secondary mt-1">🎬 {s.visual}</p>}
                  </div>
                ))}</div>
              )}
              {result.slides && (
                <div className="space-y-2">{result.slides.map((s: any, i: number) => (
                  <div key={i} className="bg-bg-surface border border-border rounded-xl p-4">
                    <span className="text-[9px] font-black uppercase text-secondary">Slide {i + 1} • {s.type}</span>
                    <p className="text-sm mt-1">{s.content}</p>
                  </div>
                ))}</div>
              )}
              {result.sections && (
                <div className="space-y-2">{result.sections.map((s: any, i: number) => (
                  <div key={i} className="bg-bg-surface border border-border rounded-xl p-4">
                    <h4 className="font-bold text-sm">{s.emoji} {s.title}</h4>
                    <p className="text-xs text-secondary mt-1">{s.content}</p>
                  </div>
                ))}</div>
              )}
              {result.cta && <div className="bg-bg-surface border border-border rounded-xl p-4"><span className="text-[9px] font-black uppercase text-secondary">CTA</span><p className="text-sm font-bold mt-1">{typeof result.cta === 'string' ? result.cta : result.cta.text}</p></div>}
              {result.hashtags && <div className="flex flex-wrap gap-1">{result.hashtags.map((h: string, i: number) => <span key={i} className="text-[10px] bg-accent-amethyst/10 text-accent-amethyst px-2 py-0.5 rounded">#{h.replace('#', '')}</span>)}</div>}
            </div>
          )}
        </div>
      )}

      {tab === 'calendar' && <CalendarTab niche={niche} />}
    </div>
  );
}

function CalendarTab({ niche }: { niche: string }) {
  const { data, isLoading } = useQuery({ queryKey: ['social-calendar', niche], queryFn: () => socialApi.calendar(niche) });
  const cal = data?.calendar;

  if (isLoading) return <div className="animate-pulse h-64 bg-bg-surface rounded-3xl" />;
  if (!cal) return <div className="text-secondary text-center py-12">Erro ao gerar calendário.</div>;

  return (
    <div className="space-y-4">
      <h2 className="font-black text-lg">📅 {cal.week_theme}</h2>
      <div className="space-y-2">
        {(cal.days || []).map((d: any, i: number) => (
          <div key={i} className="bg-bg-surface border border-border rounded-xl p-4 flex items-center gap-4">
            <div className="w-16 text-center">
              <div className="text-xs font-black uppercase text-accent-amethyst">{d.day}</div>
              <div className="text-[10px] text-secondary">{d.best_time}</div>
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <span className="text-[9px] bg-accent-amethyst/10 text-accent-amethyst px-2 py-0.5 rounded font-bold uppercase">{d.type}</span>
                <span className="font-bold text-sm">{d.topic}</span>
              </div>
              <p className="text-[11px] text-secondary mt-0.5">{d.hook || d.caption_idea}</p>
            </div>
          </div>
        ))}
      </div>
      {cal.tips && <div className="bg-accent-amethyst/10 rounded-xl p-4 text-xs italic">{cal.tips}</div>}
    </div>
  );
}

function F({ label, children }: { label: string; children: React.ReactNode }) {
  return <div><label className="text-[10px] uppercase font-black tracking-widest text-secondary mb-1.5 block">{label}</label>{children}</div>;
}
