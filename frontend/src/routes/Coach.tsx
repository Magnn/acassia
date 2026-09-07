import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import {
  Wand2, Copy, RefreshCw, Sparkles, Brain,
  CheckCircle2, BadgeCheck, Activity, AlertCircle, TrendingUp,
} from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { coachApi, type CopyVariation, type CopyRewrite, type GeneratedPersona, type FunnelReview } from '../api/coach';
import { blueprintsApi } from '../api/blueprints';
import { handleApiError } from '../lib/handleApiError';
import { toast } from '../lib/toast';

type Tab = 'copy' | 'rewrite' | 'persona' | 'review';

export default function Coach() {
  const [tab, setTab] = useState<Tab>('copy');

  return (
    <div className="p-10 max-w-5xl mx-auto space-y-8">
      <div>
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-2xl bg-accent-amethyst/10 flex items-center justify-center">
            <Brain className="w-5 h-5 text-accent-amethyst" />
          </div>
          <h1 className="text-3xl font-black tracking-tight">Meu Mistério Coach</h1>
        </div>
        <p className="text-secondary text-sm font-medium">
          IA assistente — gera copy, reescreve mensagens, cria persona.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-border overflow-x-auto">
        {([
          ['copy', 'Gerar Copy', Wand2],
          ['rewrite', 'Reescrever', RefreshCw],
          ['persona', 'Persona', BadgeCheck],
          ['review', 'Review do Funil', Activity],
        ] as Array<[Tab, string, typeof Wand2]>).map(([k, label, Icon]) => (
          <button
            key={k}
            onClick={() => setTab(k)}
            className={`px-5 py-3 text-xs font-black uppercase tracking-widest border-b-2 transition-all flex items-center gap-2 whitespace-nowrap ${
              tab === k
                ? 'border-accent-amethyst text-accent-amethyst'
                : 'border-transparent text-secondary hover:text-primary'
            }`}
          >
            <Icon className="w-3.5 h-3.5" />
            {label}
          </button>
        ))}
      </div>

      {tab === 'copy' && <CopyGenTab />}
      {tab === 'rewrite' && <RewriteTab />}
      {tab === 'persona' && <PersonaGenTab />}
      {tab === 'review' && <FunnelReviewTab />}
    </div>
  );
}


function FunnelReviewTab() {
  const [selectedFlow, setSelectedFlow] = useState<{ id: number; slug: string; title: string } | null>(null);
  const [periodDays, setPeriodDays] = useState(30);
  const [review, setReview] = useState<FunnelReview | null>(null);
  const [funnelSummary, setFunnelSummary] = useState<{
    conversion_pct: number;
    unique_leads: number;
    high_drop_nodes: string[];
  } | null>(null);
  const [lowConfidence, setLowConfidence] = useState<string | null>(null);

  const { data: flows } = useQuery({
    queryKey: ['blueprints'],
    queryFn: blueprintsApi.list,
  });

  const reviewMut = useMutation({
    mutationFn: () => {
      if (!selectedFlow) throw new Error('flow não selecionado');
      return coachApi.funnelReview({
        flow_id: selectedFlow.id,
        period_days: periodDays,
      });
    },
    onSuccess: (res) => {
      if (res.low_confidence) {
        setLowConfidence(res.message || 'Dados insuficientes pra review.');
        setReview(null);
        return;
      }
      setLowConfidence(null);
      setReview(res.review || null);
      setFunnelSummary(res.funnel_summary || null);
      toast.success(`Review gerado — score ${res.review?.overall_score ?? '?'}/100`);
    },
    onError: handleApiError('Erro ao gerar review'),
  });

  return (
    <div className="space-y-6">
      <div className="bg-bg-surface border border-border rounded-3xl p-6 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-[1fr_auto] gap-3 items-end">
          <div>
            <label className="text-[10px] uppercase font-black tracking-widest text-secondary mb-1.5 block">
              Fluxo a analisar
            </label>
            <select
              value={selectedFlow?.id || ''}
              onChange={(e) => {
                const id = Number(e.target.value) || null;
                const f = (flows ?? []).find((x) => x.id === id);
                setSelectedFlow(f ? { id: f.id, slug: f.slug, title: f.title } : null);
              }}
              className="w-full bg-bg-primary border border-border rounded-xl px-4 py-2.5 text-sm"
            >
              <option value="">Selecione…</option>
              {(flows ?? []).map((f) => (
                <option key={f.id} value={f.id}>{f.title}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-[10px] uppercase font-black tracking-widest text-secondary mb-1.5 block">
              Período
            </label>
            <select
              value={periodDays}
              onChange={(e) => setPeriodDays(Number(e.target.value))}
              className="bg-bg-primary border border-border rounded-xl px-4 py-2.5 text-sm"
            >
              <option value={7}>7 dias</option>
              <option value={14}>14 dias</option>
              <option value={30}>30 dias</option>
              <option value={60}>60 dias</option>
              <option value={90}>90 dias</option>
            </select>
          </div>
        </div>

        <button
          onClick={() => reviewMut.mutate()}
          disabled={!selectedFlow || reviewMut.isPending}
          className="w-full px-5 py-3 bg-accent-amethyst hover:bg-accent-amethyst/90 disabled:opacity-30 text-white rounded-xl text-sm font-black uppercase tracking-widest flex items-center justify-center gap-2"
        >
          <Brain className="w-4 h-4" />
          {reviewMut.isPending ? 'Analisando…' : 'Gerar review'}
        </button>
      </div>

      {lowConfidence && (
        <div className="bg-amber-500/10 border border-amber-500/30 rounded-2xl p-4 flex items-start gap-2">
          <AlertCircle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
          <div className="text-sm">
            <div className="font-black text-amber-300 mb-1">Confiança baixa</div>
            <p className="text-amber-200/80 text-xs">{lowConfidence}</p>
          </div>
        </div>
      )}

      {review && (
        <div className="space-y-4">
          {/* Score header */}
          <div className="bg-bg-surface border border-border rounded-3xl p-6 flex items-center justify-between">
            <div>
              <div className="text-[10px] uppercase font-black tracking-widest text-secondary mb-1">
                Score do funil
              </div>
              <div className="text-5xl font-black">
                {review.overall_score}<span className="text-secondary text-2xl">/100</span>
              </div>
              {review.key_metric_callout && (
                <p className="text-sm text-secondary mt-2 max-w-md">
                  {review.key_metric_callout}
                </p>
              )}
            </div>
            {funnelSummary && (
              <div className="text-right space-y-1">
                <div className="text-[10px] uppercase tracking-widest text-secondary font-black">
                  {funnelSummary.unique_leads} leads · {funnelSummary.conversion_pct}% conv
                </div>
                {funnelSummary.high_drop_nodes.length > 0 && (
                  <div className="text-[10px] text-rose-400 font-bold">
                    Nós críticos: {funnelSummary.high_drop_nodes.length}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Strengths */}
          {review.strengths?.length > 0 && (
            <div className="bg-emerald-500/5 border border-emerald-500/30 rounded-3xl p-5">
              <h3 className="text-[10px] font-black uppercase tracking-widest text-emerald-400 mb-3 flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5" />
                Pontos fortes
              </h3>
              <ul className="space-y-2">
                {review.strengths.map((s, i) => (
                  <li key={i} className="text-sm flex gap-2">
                    <span className="text-emerald-400">✓</span>
                    <span>{s}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Opportunities */}
          {review.opportunities?.length > 0 && (
            <div className="bg-bg-surface border border-border rounded-3xl p-5">
              <h3 className="text-[10px] font-black uppercase tracking-widest text-secondary mb-3 flex items-center gap-1.5">
                <TrendingUp className="w-3.5 h-3.5 text-accent-amethyst" />
                Oportunidades de melhoria ({review.opportunities.length})
              </h3>
              <ol className="space-y-3">
                {review.opportunities.map((op, i) => (
                  <li key={i} className="bg-bg-primary border border-border rounded-xl p-3">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-[10px] uppercase font-black tracking-widest text-accent-amethyst">
                        {i + 1}
                      </span>
                      {op.node_id && (
                        <span className="text-[10px] font-mono bg-bg-surface px-2 py-0.5 rounded">
                          {op.node_id}
                        </span>
                      )}
                    </div>
                    <div className="text-sm text-rose-300 mb-1">{op.issue}</div>
                    <div className="text-[12px] text-emerald-300">→ {op.suggestion}</div>
                  </li>
                ))}
              </ol>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function CopyGenTab() {
  const [intent, setIntent] = useState('');
  const [tone, setTone] = useState<'casual' | 'formal' | 'consultivo' | 'direto'>('casual');
  const [length, setLength] = useState<'curto' | 'medium' | 'longo'>('medium');
  const [includeCta, setIncludeCta] = useState(false);
  const [variations, setVariations] = useState<CopyVariation[]>([]);

  const genMut = useMutation({
    mutationFn: () => coachApi.generateCopy({ intent, tone, length, include_cta: includeCta }),
    onSuccess: (res) => {
      setVariations(res.variations);
      toast.success(`${res.variations.length} variações geradas`);
    },
    onError: handleApiError('Erro ao gerar copy'),
  });

  return (
    <div className="space-y-6">
      <div className="bg-bg-surface border border-border rounded-3xl p-6 space-y-4">
        <div>
          <label className="text-[10px] uppercase font-black tracking-widest text-secondary mb-1.5 block">
            O que você quer comunicar?
          </label>
          <textarea
            value={intent}
            onChange={(e) => setIntent(e.target.value)}
            rows={3}
            placeholder="Ex: oferecer proposta exclusiva com 20% de desconto para fechamento hoje no WhatsApp"
            className="w-full bg-bg-primary border border-border rounded-xl px-4 py-3 text-sm placeholder:text-secondary/40 focus:outline-none focus:border-accent-amethyst/30 resize-none"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-[10px] uppercase font-black tracking-widest text-secondary mb-1.5 block">Tom</label>
            <div className="flex gap-2 flex-wrap">
              {(['casual', 'formal', 'consultivo', 'direto'] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => setTone(t)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold capitalize ${
                    tone === t ? 'bg-accent-amethyst text-white' : 'bg-bg-primary text-secondary hover:text-primary'
                  }`}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="text-[10px] uppercase font-black tracking-widest text-secondary mb-1.5 block">Comprimento</label>
            <div className="flex gap-2">
              {(['curto', 'medium', 'longo'] as const).map((l) => (
                <button
                  key={l}
                  onClick={() => setLength(l)}
                  className={`flex-1 px-3 py-1.5 rounded-lg text-xs font-bold ${
                    length === l ? 'bg-accent-amethyst text-white' : 'bg-bg-primary text-secondary hover:text-primary'
                  }`}
                >
                  {l}
                </button>
              ))}
            </div>
          </div>
        </div>

        <label className="flex items-center gap-2 text-xs cursor-pointer">
          <input
            type="checkbox"
            checked={includeCta}
            onChange={(e) => setIncludeCta(e.target.checked)}
          />
          Incluir CTA (call-to-action) no final
        </label>

        <button
          onClick={() => genMut.mutate()}
          disabled={!intent.trim() || genMut.isPending}
          className="w-full px-5 py-3 bg-accent-amethyst hover:bg-accent-amethyst/90 disabled:opacity-30 text-white rounded-2xl text-sm font-black uppercase tracking-widest flex items-center justify-center gap-2"
        >
          <Sparkles className="w-4 h-4" />
          {genMut.isPending ? 'Gerando 5 variações...' : 'Gerar 5 variações'}
        </button>
      </div>

      {variations.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-[10px] font-black uppercase tracking-widest text-secondary">
            Variações ({variations.length})
          </h3>
          {variations.map((v, i) => (
            <VariationCard key={i} text={v.text} label={v.style} index={i} />
          ))}
        </div>
      )}
    </div>
  );
}

function RewriteTab() {
  const [original, setOriginal] = useState('');
  const [targetTone, setTargetTone] = useState('casual');
  const [rewrites, setRewrites] = useState<CopyRewrite[]>([]);

  const rewriteMut = useMutation({
    mutationFn: () => coachApi.rewriteCopy({ original, target_tone: targetTone, count: 3 }),
    onSuccess: (res) => {
      setRewrites(res.rewrites);
      toast.success(`${res.rewrites.length} reescritas geradas`);
    },
    onError: handleApiError('Erro ao reescrever'),
  });

  return (
    <div className="space-y-6">
      <div className="bg-bg-surface border border-border rounded-3xl p-6 space-y-4">
        <div>
          <label className="text-[10px] uppercase font-black tracking-widest text-secondary mb-1.5 block">
            Mensagem original (que tá com drop alto)
          </label>
          <textarea
            value={original}
            onChange={(e) => setOriginal(e.target.value)}
            rows={4}
            placeholder="Cole aqui a mensagem que quer reescrever..."
            className="w-full bg-bg-primary border border-border rounded-xl px-4 py-3 text-sm placeholder:text-secondary/40 focus:outline-none focus:border-accent-amethyst/30 resize-none"
          />
        </div>
        <div>
          <label className="text-[10px] uppercase font-black tracking-widest text-secondary mb-1.5 block">Tom alvo</label>
          <div className="flex gap-2">
            {['casual', 'formal', 'consultivo', 'direto'].map((t) => (
              <button
                key={t}
                onClick={() => setTargetTone(t)}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold capitalize ${
                  targetTone === t ? 'bg-accent-amethyst text-white' : 'bg-bg-primary text-secondary'
                }`}
              >
                {t}
              </button>
            ))}
          </div>
        </div>
        <button
          onClick={() => rewriteMut.mutate()}
          disabled={!original.trim() || rewriteMut.isPending}
          className="w-full px-5 py-3 bg-accent-amethyst hover:bg-accent-amethyst/90 disabled:opacity-30 text-white rounded-2xl text-sm font-black uppercase tracking-widest flex items-center justify-center gap-2"
        >
          <RefreshCw className="w-4 h-4" />
          {rewriteMut.isPending ? 'Reescrevendo...' : 'Reescrever (3 versões)'}
        </button>
      </div>

      {rewrites.length > 0 && (
        <div className="space-y-3">
          {rewrites.map((r, i) => (
            <VariationCard key={i} text={r.text} label={r.improvement_reason} index={i} />
          ))}
        </div>
      )}
    </div>
  );
}

function PersonaGenTab() {
  const [tom, setTom] = useState('consultivo');
  const [energia, setEnergia] = useState('media');
  const [emojiLevel, setEmojiLevel] = useState('moderado');
  const [length, setLength] = useState('medium');
  const [specialty, setSpecialty] = useState('vendas');
  const [name, setName] = useState('');
  const [persona, setPersona] = useState<GeneratedPersona | null>(null);

  const genMut = useMutation({
    mutationFn: () => coachApi.generatePersona({
      tom, energia, emoji_level: emojiLevel, length, specialty, name: name || undefined,
    }),
    onSuccess: (res) => setPersona(res.persona),
    onError: handleApiError('Erro ao gerar persona'),
  });

  return (
    <div className="space-y-6">
      <div className="bg-bg-surface border border-border rounded-3xl p-6 space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <PickerField label="Tom" value={tom} onChange={setTom} options={['casual', 'formal', 'consultivo', 'direto']} />
          <PickerField label="Energia" value={energia} onChange={setEnergia} options={['calma', 'media', 'energetica', 'direta']} />
          <PickerField label="Emojis" value={emojiLevel} onChange={setEmojiLevel} options={['nenhum', 'moderado', 'muitos']} />
          <PickerField label="Comprimento" value={length} onChange={setLength} options={['curto', 'medium', 'longo']} />
          <PickerField label="Especialidade" value={specialty} onChange={setSpecialty} options={['vendas', 'suporte', 'reativacao', 'qualificacao', 'geral']} />
          <div>
            <label className="text-[10px] uppercase font-black tracking-widest text-secondary mb-1.5 block">Nome (opcional)</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Sugerir um"
              className="w-full bg-bg-primary border border-border rounded-xl px-3 py-1.5 text-sm focus:outline-none focus:border-accent-amethyst/30"
            />
          </div>
        </div>
        <button
          onClick={() => genMut.mutate()}
          disabled={genMut.isPending}
          className="w-full px-5 py-3 bg-accent-amethyst hover:bg-accent-amethyst/90 disabled:opacity-30 text-white rounded-2xl text-sm font-black uppercase tracking-widest flex items-center justify-center gap-2"
        >
          <BadgeCheck className="w-4 h-4" />
          {genMut.isPending ? 'Criando persona...' : 'Gerar persona'}
        </button>
      </div>

      {persona && (
        <div className="bg-gradient-to-br from-accent-amethyst/10 to-purple-500/5 border border-accent-amethyst/20 rounded-3xl p-6 space-y-4">
          <div>
            <div className="text-[10px] font-black uppercase tracking-widest text-accent-amethyst">Nome</div>
            <div className="text-2xl font-black tracking-tight">{persona.name}</div>
          </div>
          <div>
            <div className="text-[10px] font-black uppercase tracking-widest text-secondary mb-1">Apresentação</div>
            <p className="text-sm text-primary leading-relaxed">{persona.presentation}</p>
          </div>
          <div>
            <div className="text-[10px] font-black uppercase tracking-widest text-secondary mb-1">Saudação template</div>
            <div className="bg-bg-primary border border-border rounded-xl p-3 text-sm italic">
              "{persona.greeting_template}"
            </div>
          </div>
          <div>
            <div className="text-[10px] font-black uppercase tracking-widest text-secondary mb-1">Estilo</div>
            <p className="text-sm">{persona.reading_style}</p>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <div className="text-[10px] font-black uppercase tracking-widest text-emerald-500 mb-2">SEMPRE</div>
              <ul className="space-y-1 text-xs">
                {persona.instructions.do.map((item, i) => (
                  <li key={i} className="flex gap-2">
                    <CheckCircle2 className="w-3 h-3 text-emerald-500 flex-shrink-0 mt-0.5" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <div className="text-[10px] font-black uppercase tracking-widest text-red-400 mb-2">NUNCA</div>
              <ul className="space-y-1 text-xs">
                {persona.instructions.dont.map((item, i) => (
                  <li key={i} className="flex gap-2">
                    <span className="text-red-400 flex-shrink-0">×</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function PickerField({
  label, value, onChange, options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: string[];
}) {
  return (
    <div>
      <label className="text-[10px] uppercase font-black tracking-widest text-secondary mb-1.5 block">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full bg-bg-primary border border-border rounded-xl px-3 py-1.5 text-sm focus:outline-none focus:border-accent-amethyst/30"
      >
        {options.map(o => (
          <option key={o} value={o} className="capitalize">{o}</option>
        ))}
      </select>
    </div>
  );
}

function VariationCard({ text, label, index }: { text: string; label: string; index: number }) {
  const copy = () => {
    navigator.clipboard.writeText(text);
    toast.success('Copiado');
  };

  return (
    <div className="bg-bg-surface border border-border rounded-2xl p-4 group hover:border-accent-amethyst/30">
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex items-center gap-2">
          <span className="font-mono text-[10px] text-secondary">#{index + 1}</span>
          <span className="text-[10px] font-black uppercase tracking-widest text-accent-amethyst bg-accent-amethyst/10 px-2 py-0.5 rounded">
            {label}
          </span>
        </div>
        <button
          onClick={copy}
          className="opacity-40 group-hover:opacity-100 text-secondary hover:text-accent-amethyst flex items-center gap-1 text-[10px] font-black uppercase tracking-widest"
        >
          <Copy className="w-3 h-3" />
          Copiar
        </button>
      </div>
      <p className="text-sm text-primary leading-relaxed whitespace-pre-wrap">{text}</p>
    </div>
  );
}
