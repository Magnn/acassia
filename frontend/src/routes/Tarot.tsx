import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { Sparkles, Shuffle, Save, Wand2 } from 'lucide-react';
import { tarotApi, type TarotCardDraw } from '../api/tarot';
import { handleApiError } from '../lib/handleApiError';
import { toast } from '../lib/toast';

export default function Tarot() {
  const [selectedSpread, setSelectedSpread] = useState('3card');
  const [drawn, setDrawn] = useState<TarotCardDraw[] | null>(null);
  const [question, setQuestion] = useState('');
  const [savedInterpretation, setSavedInterpretation] = useState<string | null>(null);

  const { data: decksData } = useQuery({
    queryKey: ['tarot-decks'],
    queryFn: tarotApi.decks,
  });

  const drawMut = useMutation({
    mutationFn: (spread_type: string) => tarotApi.draw({ spread_type }),
    onSuccess: (res) => {
      setDrawn(res.cards);
      setSavedInterpretation(null);
    },
    onError: handleApiError('Erro ao tirar cartas'),
  });

  const saveMut = useMutation({
    mutationFn: () =>
      tarotApi.saveReading({
        spread_type: selectedSpread,
        cards: drawn!,
        question: question || undefined,
        generate_interpretation: true,
      }),
    onSuccess: (res) => {
      toast.success('Leitura salva');
      setSavedInterpretation(res.interpretation);
    },
    onError: handleApiError('Erro ao salvar'),
  });

  const spreads = decksData?.spreads ?? [];

  return (
    <div className="p-10 max-w-5xl mx-auto space-y-8">
      <div>
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-2xl bg-accent-amethyst/10 flex items-center justify-center">
            <Wand2 className="w-5 h-5 text-accent-amethyst" />
          </div>
          <h1 className="text-3xl font-black tracking-tight">Tarot Virtual</h1>
        </div>
        <p className="text-secondary text-sm font-medium">
          Tire cartas, gere interpretação com IA e mande pro lead.
        </p>
      </div>

      {/* Spread picker */}
      <div className="bg-bg-surface border border-border rounded-3xl p-6">
        <h3 className="text-[10px] font-black uppercase tracking-widest text-secondary mb-3">
          Tipo de tiragem
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {spreads.map((s) => (
            <button
              key={s.key}
              onClick={() => setSelectedSpread(s.key)}
              className={`p-4 rounded-2xl border text-left transition-all ${
                selectedSpread === s.key
                  ? 'bg-accent-amethyst/10 border-accent-amethyst'
                  : 'bg-bg-primary border-border hover:border-accent-amethyst/30'
              }`}
            >
              <div className="font-black text-sm">{s.name}</div>
              <div className="text-[10px] text-secondary mt-1">
                {s.positions.length} carta{s.positions.length > 1 ? 's' : ''}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Question */}
      <div>
        <label className="text-[10px] uppercase font-black tracking-widest text-secondary mb-2 block">
          Pergunta (opcional)
        </label>
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          rows={2}
          placeholder="Ex: meu amor vai voltar? Como vai meu trabalho?"
          className="w-full bg-bg-surface border border-border rounded-2xl px-4 py-3 text-sm placeholder:text-secondary/40 focus:outline-none focus:border-accent-amethyst/30 resize-none"
        />
      </div>

      {/* Draw button */}
      <div className="text-center">
        <button
          onClick={() => drawMut.mutate(selectedSpread)}
          disabled={drawMut.isPending}
          className="px-8 py-4 bg-gradient-to-r from-accent-amethyst to-purple-600 hover:scale-105 disabled:opacity-30 disabled:cursor-not-allowed text-white rounded-2xl font-black uppercase tracking-widest text-sm shadow-2xl flex items-center gap-3 mx-auto"
        >
          <Shuffle className="w-5 h-5" />
          {drawMut.isPending ? 'Embaralhando...' : 'Tirar cartas'}
        </button>
      </div>

      {/* Cards */}
      {drawn && (
        <>
          <div
            className={`grid gap-4 ${
              drawn.length === 1 ? 'grid-cols-1 max-w-xs mx-auto' :
              drawn.length === 3 ? 'grid-cols-3' :
              drawn.length === 5 ? 'grid-cols-5' :
              'grid-cols-2 md:grid-cols-5'
            }`}
          >
            {drawn.map((c, i) => (
              <CardView key={i} card={c} index={i} />
            ))}
          </div>

          {/* Save / interpretation */}
          <div className="bg-bg-surface border border-border rounded-3xl p-6 space-y-4">
            {savedInterpretation ? (
              <>
                <h3 className="text-sm font-black flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-accent-amethyst" />
                  Interpretação IA
                </h3>
                <div className="prose prose-sm prose-invert text-primary whitespace-pre-wrap leading-relaxed">
                  {savedInterpretation}
                </div>
              </>
            ) : (
              <div className="text-center space-y-3">
                <p className="text-sm text-secondary">
                  Gostou da tiragem? Salve com interpretação IA + mande pro lead.
                </p>
                <button
                  onClick={() => saveMut.mutate()}
                  disabled={saveMut.isPending}
                  className="px-6 py-3 bg-accent-amethyst hover:bg-accent-amethyst/90 disabled:opacity-30 text-white rounded-2xl font-black uppercase tracking-widest text-xs flex items-center gap-2 mx-auto"
                >
                  <Save className="w-4 h-4" />
                  {saveMut.isPending ? 'Gerando interpretação...' : 'Salvar + interpretar'}
                </button>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

function CardView({ card, index }: { card: TarotCardDraw; index: number }) {
  return (
    <div
      className={`bg-gradient-to-br from-purple-900/40 to-indigo-900/40 border-2 border-accent-amethyst/30 rounded-3xl p-4 transition-all hover:scale-105 hover:border-accent-amethyst ${
        card.reversed ? 'rotate-180' : ''
      }`}
      style={{
        animationDelay: `${index * 100}ms`,
        animation: 'flipIn 600ms ease-out forwards',
      }}
    >
      <div className={card.reversed ? 'rotate-180' : ''}>
        <div className="text-[9px] font-black uppercase tracking-widest text-accent-amethyst mb-1">
          {card.position}
        </div>
        <div className="aspect-[2/3] bg-purple-950/60 rounded-xl flex items-center justify-center mb-2 border border-accent-amethyst/20">
          {card.image_url ? (
            <img src={card.image_url} alt={card.name} className="w-full h-full object-cover rounded-xl" />
          ) : (
            <Sparkles className="w-12 h-12 text-accent-amethyst/40" />
          )}
        </div>
        <div className="font-black text-xs text-white">{card.name}</div>
        {card.reversed && (
          <div className="text-[9px] text-amber-400 uppercase mt-0.5">Invertida</div>
        )}
        <div className="text-[10px] text-zinc-400 mt-2 line-clamp-3">{card.meaning}</div>
      </div>
    </div>
  );
}
