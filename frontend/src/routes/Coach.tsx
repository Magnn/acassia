import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import {
  Wand2, Copy, RefreshCw, Sparkles, Brain,
  CheckCircle2, BadgeCheck,
} from 'lucide-react';
import { coachApi, type CopyVariation, type CopyRewrite, type GeneratedPersona } from '../api/coach';
import { handleApiError } from '../lib/handleApiError';
import { toast } from '../lib/toast';

type Tab = 'copy' | 'rewrite' | 'persona';

export default function Coach() {
  const [tab, setTab] = useState<Tab>('copy');

  return (
    <div className="p-10 max-w-5xl mx-auto space-y-8">
      <div>
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-2xl bg-accent-amethyst/10 flex items-center justify-center">
            <Brain className="w-5 h-5 text-accent-amethyst" />
          </div>
          <h1 className="text-3xl font-black tracking-tight">Cigana Coach</h1>
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
    </div>
  );
}

function CopyGenTab() {
  const [intent, setIntent] = useState('');
  const [tone, setTone] = useState<'casual' | 'formal' | 'mistico' | 'direto'>('casual');
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
            placeholder="Ex: oferecer tarô do amor por R$67 com leitura em áudio em 1h"
            className="w-full bg-bg-primary border border-border rounded-xl px-4 py-3 text-sm placeholder:text-secondary/40 focus:outline-none focus:border-accent-amethyst/30 resize-none"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-[10px] uppercase font-black tracking-widest text-secondary mb-1.5 block">Tom</label>
            <div className="flex gap-2 flex-wrap">
              {(['casual', 'formal', 'mistico', 'direto'] as const).map((t) => (
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
            {['casual', 'formal', 'mistico', 'direto'].map((t) => (
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
  const [tom, setTom] = useState('casual');
  const [energia, setEnergia] = useState('media');
  const [emojiLevel, setEmojiLevel] = useState('moderado');
  const [length, setLength] = useState('medium');
  const [specialty, setSpecialty] = useState('amor');
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
          <PickerField label="Tom" value={tom} onChange={setTom} options={['casual', 'formal', 'mistico', 'direto']} />
          <PickerField label="Energia" value={energia} onChange={setEnergia} options={['calma', 'media', 'energetica', 'poetica']} />
          <PickerField label="Emojis" value={emojiLevel} onChange={setEmojiLevel} options={['nenhum', 'moderado', 'muitos']} />
          <PickerField label="Comprimento" value={length} onChange={setLength} options={['curto', 'medium', 'longo']} />
          <PickerField label="Especialidade" value={specialty} onChange={setSpecialty} options={['amor', 'dinheiro', 'protecao', 'espiritualidade', 'geral']} />
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
