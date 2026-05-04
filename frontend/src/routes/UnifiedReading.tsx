import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Wand2, Upload, Sparkles, Clock, BookOpen, Sun, Moon as MoonIcon, Star, Share2 } from 'lucide-react';
import { api } from '../api/client';
import { handleApiError } from '../lib/handleApiError';
import { toast } from '../lib/toast';

const readingApi = {
  unified: (b: { question?: string; birth_date?: string; birth_time?: string; birth_city?: string; name?: string }) =>
    api.post<{ ok: boolean; reading: any }>('/saas/reading/unified', b),
  palm: (b: { image_base64: string; question?: string }) =>
    api.post<{ ok: boolean; palm_reading: any }>('/saas/reading/palm', b),
  daily: () => api.get<{ ok: boolean; reading: any }>('/saas/reading/daily'),
  history: (page?: number) => api.get<{ readings: any[]; total: number }>(`/saas/reading/history?page=${page || 1}`),
};

export default function UnifiedReading() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<'daily' | 'unified' | 'palm' | 'history'>('daily');

  return (
    <div className="p-10 max-w-4xl mx-auto space-y-8">
      <div className="flex items-center gap-3 mb-2">
        <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-accent-amethyst to-pink-500 flex items-center justify-center">
          <Wand2 className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="text-3xl font-black tracking-tight">Leitura Multi-Modal</h1>
          <p className="text-secondary text-sm">Tarot + Astrologia + Numerologia + Lua — tudo integrado.</p>
        </div>
      </div>

      <div className="flex gap-2 border-b border-border pb-3">
        {[
          { id: 'daily' as const, icon: Sun, label: 'Diária' },
          { id: 'unified' as const, icon: Sparkles, label: 'Integrada' },
          { id: 'palm' as const, icon: Upload, label: 'Palma' },
          { id: 'history' as const, icon: Clock, label: 'Histórico' },
        ].map(t => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-black uppercase tracking-widest transition-all ${tab === t.id ? 'bg-accent-amethyst text-white' : 'bg-bg-surface text-secondary hover:bg-bg-surface/80'}`}>
            <t.icon className="w-3.5 h-3.5" /> {t.label}
          </button>
        ))}
      </div>

      {tab === 'daily' && <DailyTab />}
      {tab === 'unified' && <UnifiedTab />}
      {tab === 'palm' && <PalmTab />}
      {tab === 'history' && <HistoryTab />}
    </div>
  );
}

function DailyTab() {
  const { data, isLoading } = useQuery({ queryKey: ['daily-reading'], queryFn: readingApi.daily });
  const r = data?.reading;

  if (isLoading) return <div className="animate-pulse h-64 bg-bg-surface rounded-3xl" />;
  if (!r) return <div className="text-secondary text-center py-12">Erro ao carregar leitura diária.</div>;

  return (
    <div className="bg-gradient-to-br from-accent-amethyst/10 to-pink-500/5 border border-accent-amethyst/20 rounded-3xl p-8 text-center space-y-4">
      <h2 className="text-2xl font-black tracking-tight">{r.title}</h2>
      {r.card && (
        <div className="bg-bg-surface/50 border border-border rounded-2xl p-5 inline-block mx-auto">
          <div className="text-4xl mb-2">🃏</div>
          <div className="font-black">{r.card.name}</div>
          <div className="text-xs text-secondary mt-1">{r.card.meaning}</div>
        </div>
      )}
      <p className="text-sm max-w-lg mx-auto">{r.message}</p>
      <div className="bg-accent-amethyst/10 rounded-xl p-4 italic text-sm text-accent-amethyst">✨ {r.affirmation}</div>
      <div className="grid grid-cols-3 gap-3 max-w-sm mx-auto">
        {[{ l: 'Energia', v: r.energy }, { l: 'Cor', v: r.color }, { l: 'Cristal', v: r.crystal }].map(i => (
          <div key={i.l} className="bg-bg-surface border border-border rounded-xl p-3 text-center">
            <div className="text-[9px] font-black uppercase text-secondary">{i.l}</div>
            <div className="text-xs font-bold capitalize mt-1">{i.v}</div>
          </div>
        ))}
      </div>
      {r.cached && <span className="text-[10px] text-secondary">Leitura de hoje já foi gerada (1/dia).</span>}
      <ShareButtons title={r.title} message={r.message} affirmation={r.affirmation} />
    </div>
  );
}

function UnifiedTab() {
  const [form, setForm] = useState({ question: '', birth_date: '', birth_time: '', birth_city: '', name: '' });
  const [result, setResult] = useState<any>(null);
  const set = (k: string, v: string) => setForm(f => ({ ...f, [k]: v }));

  const mut = useMutation({
    mutationFn: () => readingApi.unified(form),
    onSuccess: (r) => { setResult(r.reading); toast.success('🔮 Leitura pronta!'); },
    onError: handleApiError('Erro na leitura'),
  });

  return (
    <div className="space-y-6">
      {!result ? (
        <div className="bg-bg-surface border border-border rounded-3xl p-8 space-y-4">
          <h3 className="font-black text-lg text-center">Sua Leitura Integrada</h3>
          <F label="Sua pergunta"><input value={form.question} onChange={e => set('question', e.target.value)} placeholder="O que o universo quer me dizer?" className="inp" /></F>
          <div className="grid grid-cols-2 gap-3">
            <F label="Nome"><input value={form.name} onChange={e => set('name', e.target.value)} placeholder="Seu nome" className="inp" /></F>
            <F label="Data nascimento"><input type="date" value={form.birth_date} onChange={e => set('birth_date', e.target.value)} className="inp" /></F>
            <F label="Hora nascimento"><input type="time" value={form.birth_time} onChange={e => set('birth_time', e.target.value)} className="inp" /></F>
            <F label="Cidade"><input value={form.birth_city} onChange={e => set('birth_city', e.target.value)} placeholder="São Paulo" className="inp" /></F>
          </div>
          <button onClick={() => mut.mutate()} disabled={mut.isPending}
            className="w-full py-4 bg-gradient-to-r from-accent-amethyst to-pink-500 hover:opacity-90 disabled:opacity-30 text-white rounded-2xl font-black uppercase tracking-widest text-sm">
            {mut.isPending ? '🔮 Gerando leitura completa...' : '✨ Gerar Leitura Multi-Modal'}
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="bg-gradient-to-br from-accent-amethyst/10 to-pink-500/5 border border-accent-amethyst/20 rounded-3xl p-6 text-center">
            <h2 className="text-xl font-black">{result.title}</h2>
          </div>
          {result.tarot?.cards && (
            <Section title="🃏 Tarot">
              <div className="grid grid-cols-3 gap-3">
                {result.tarot.cards.map((c: any, i: number) => (
                  <div key={i} className="bg-bg-surface/50 rounded-xl p-4 text-center">
                    <div className="text-[9px] font-black uppercase text-secondary mb-1">{c.position}</div>
                    <div className="font-bold text-sm">{c.name}</div>
                    <div className="text-[11px] text-secondary mt-1">{c.meaning}</div>
                  </div>
                ))}
              </div>
              {result.tarot.synthesis && <p className="text-sm text-secondary mt-2">{result.tarot.synthesis}</p>}
            </Section>
          )}
          {result.astrology && (
            <Section title="⭐ Astrologia">
              <p className="text-sm"><strong>Signo:</strong> {result.astrology.sun_sign}</p>
              <p className="text-sm text-secondary">{result.astrology.current_transit}</p>
              <p className="text-sm italic mt-1">{result.astrology.advice}</p>
            </Section>
          )}
          {result.numerology && (
            <Section title="🔢 Numerologia">
              <p className="text-sm"><strong>Caminho de Vida:</strong> {result.numerology.life_path}</p>
              <p className="text-sm text-secondary">{result.numerology.meaning}</p>
            </Section>
          )}
          {result.lunar && (
            <Section title="🌙 Lunar">
              <p className="text-sm"><strong>Fase:</strong> {result.lunar.phase}</p>
              <p className="text-sm text-secondary">{result.lunar.influence}</p>
              <p className="text-sm italic mt-1">Ritual: {result.lunar.ritual_suggestion}</p>
            </Section>
          )}
          <div className="bg-gradient-to-br from-accent-amethyst/10 to-pink-500/5 border border-accent-amethyst/20 rounded-2xl p-6">
            <h3 className="font-black text-sm mb-2">🔮 Mensagem Integrada</h3>
            <p className="text-sm whitespace-pre-wrap">{result.integrated_message}</p>
          </div>
          {result.affirmation && <div className="bg-accent-amethyst/10 rounded-xl p-4 text-center italic text-sm text-accent-amethyst">✨ {result.affirmation}</div>}
          {result.lucky && (
            <div className="grid grid-cols-4 gap-2">
              {[{ l: 'Cor', v: result.lucky.color }, { l: 'Cristal', v: result.lucky.crystal }, { l: 'Número', v: result.lucky.number }, { l: 'Elemento', v: result.lucky.element }].map(i => (
                <div key={i.l} className="bg-bg-surface border border-border rounded-xl p-3 text-center">
                  <div className="text-[9px] font-black uppercase text-secondary">{i.l}</div>
                  <div className="text-xs font-bold capitalize mt-1">{i.v}</div>
                </div>
              ))}
            </div>
          )}
          <ShareButtons title={result.title} message={result.integrated_message} affirmation={result.affirmation} />
          <button onClick={() => setResult(null)} className="w-full py-3 bg-bg-surface border border-border rounded-2xl font-bold text-sm">Nova Leitura</button>
        </div>
      )}
    </div>
  );
}

function PalmTab() {
  const [image, setImage] = useState<string | null>(null);
  const [question, setQuestion] = useState('');
  const [result, setResult] = useState<any>(null);

  const mut = useMutation({
    mutationFn: () => readingApi.palm({ image_base64: image!, question }),
    onSuccess: (r) => { setResult(r.palm_reading); toast.success('🖐️ Leitura da palma pronta!'); },
    onError: handleApiError('Erro na leitura'),
  });

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => setImage(ev.target?.result as string);
    reader.readAsDataURL(file);
  };

  return (
    <div className="space-y-6">
      {!result ? (
        <div className="bg-bg-surface border border-border rounded-3xl p-8 space-y-4 text-center">
          <h3 className="font-black text-lg">🖐️ Quiromancia IA</h3>
          <p className="text-secondary text-sm">Tire uma foto da palma da sua mão aberta e a IA faz a leitura.</p>
          {image ? (
            <div className="relative inline-block"><img src={image} alt="Palma" className="w-48 h-48 object-cover rounded-2xl mx-auto border border-accent-amethyst/30" />
              <button onClick={() => setImage(null)} className="absolute -top-2 -right-2 w-6 h-6 bg-red-500 text-white rounded-full text-xs font-bold">✕</button>
            </div>
          ) : (
            <label className="block cursor-pointer"><div className="border-2 border-dashed border-border rounded-2xl p-12 hover:border-accent-amethyst/30 transition-all">
              <Upload className="w-12 h-12 mx-auto text-secondary/40 mb-3" /><span className="text-sm font-bold">Clique para enviar foto</span>
            </div><input type="file" accept="image/*" className="hidden" onChange={handleFile} /></label>
          )}
          <F label="Pergunta (opcional)"><input value={question} onChange={e => setQuestion(e.target.value)} placeholder="Sobre minha vida amorosa..." className="inp" /></F>
          <button onClick={() => mut.mutate()} disabled={!image || mut.isPending}
            className="w-full py-4 bg-gradient-to-r from-accent-amethyst to-pink-500 disabled:opacity-30 text-white rounded-2xl font-black uppercase tracking-widest text-sm">
            {mut.isPending ? '🔮 Analisando...' : '🖐️ Analisar Palma'}
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          <h2 className="text-xl font-black text-center">{result.title || 'Leitura da Palma'}</h2>
          {['life_line', 'heart_line', 'head_line', 'destiny_line'].map(key => result[key] && (
            <Section key={key} title={{'life_line': '🫀 Linha da Vida', 'heart_line': '💜 Linha do Coração', 'head_line': '🧠 Linha da Cabeça', 'destiny_line': '⭐ Linha do Destino'}[key] || key}>
              <p className="text-sm"><strong>Observação:</strong> {result[key].description}</p>
              <p className="text-sm text-secondary mt-1">{result[key].interpretation}</p>
            </Section>
          ))}
          {result.overall_message && <div className="bg-accent-amethyst/10 rounded-xl p-4 text-sm">{result.overall_message}</div>}
          {result.advice && <div className="bg-bg-surface border border-border rounded-xl p-4 italic text-sm">{result.advice}</div>}
          <button onClick={() => { setResult(null); setImage(null); }} className="w-full py-3 bg-bg-surface border border-border rounded-2xl font-bold text-sm">Nova Leitura</button>
        </div>
      )}
    </div>
  );
}

function HistoryTab() {
  const { data, isLoading } = useQuery({ queryKey: ['reading-history'], queryFn: () => readingApi.history() });
  const readings = data?.readings ?? [];

  if (isLoading) return <div className="animate-pulse space-y-3">{[1,2,3].map(i => <div key={i} className="h-16 bg-bg-surface rounded-xl" />)}</div>;

  return (
    <div className="space-y-3">
      {readings.length === 0 ? (
        <div className="text-center py-16 space-y-3"><div className="text-5xl">🔮</div><h3 className="text-lg font-black">O universo ainda não falou</h3><p className="text-secondary text-sm max-w-sm mx-auto">Sua primeira leitura é gratuita. Toque em "Diária" e descubra o que as cartas revelam hoje.</p></div>
      ) : readings.map((r: any) => (
        <div key={r.id} className="bg-bg-surface border border-border rounded-xl p-4 flex items-center justify-between">
          <div>
            <div className="font-bold text-sm">{r.summary || r.question}</div>
            <span className="text-[10px] text-secondary">{r.cards} cartas • {r.created_at ? new Date(r.created_at).toLocaleDateString('pt-BR') : ''}</span>
          </div>
          <BookOpen className="w-4 h-4 text-secondary" />
        </div>
      ))}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return <div className="bg-bg-surface border border-border rounded-2xl p-5"><h3 className="font-black text-sm mb-3">{title}</h3>{children}</div>;
}
function F({ label, children }: { label: string; children: React.ReactNode }) {
  return <div><label className="text-[10px] uppercase font-black tracking-widest text-secondary mb-1.5 block">{label}</label>{children}</div>;
}

function ShareButtons({ title, message, affirmation }: { title?: string; message?: string; affirmation?: string }) {
  const text = `🔮 ${title || 'Minha Leitura'}\n\n${(message || '').slice(0, 200)}...\n\n✨ ${affirmation || ''}\n\n🌟 Descubra a sua em meumisterio.com`;
  const waUrl = `https://api.whatsapp.com/send?text=${encodeURIComponent(text)}`;
  const shareNative = () => { if (navigator.share) { navigator.share({ title: title || 'Leitura', text }); } else { navigator.clipboard.writeText(text); toast.success('Copiado!'); } };
  return (
    <div className="flex gap-2 justify-center">
      <a href={waUrl} target="_blank" rel="noreferrer" className="flex items-center gap-2 px-4 py-2 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-xl text-xs font-black hover:bg-emerald-500/20 transition-all">
        📲 WhatsApp
      </a>
      <button onClick={shareNative} className="flex items-center gap-2 px-4 py-2 bg-accent-amethyst/10 text-accent-amethyst border border-accent-amethyst/20 rounded-xl text-xs font-black hover:bg-accent-amethyst/20 transition-all">
        <Share2 className="w-3.5 h-3.5" /> Compartilhar
      </button>
    </div>
  );
}
