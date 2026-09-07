import { useEffect, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Sparkles, Shuffle, Save, Wand2, Search, Send,
  RefreshCw, Trash2, History, Check,
} from 'lucide-react';
import { tarotApi, type TarotCardDraw, type TarotReading } from '../api/tarot';
import { inboxApi, type LeadPreview } from '../api/inbox';
import { handleApiError } from '../lib/handleApiError';
import { toast } from '../lib/toast';

export default function Tarot() {
  const qc = useQueryClient();
  const [selectedSpread, setSelectedSpread] = useState('3card');
  const [drawn, setDrawn] = useState<TarotCardDraw[] | null>(null);
  const [question, setQuestion] = useState('');
  const [savedReadingId, setSavedReadingId] = useState<number | null>(null);
  const [savedInterpretation, setSavedInterpretation] = useState<string | null>(null);
  const [selectedLeadId, setSelectedLeadId] = useState<number | null>(null);
  const [historyOpen, setHistoryOpen] = useState(false);

  const { data: decksData } = useQuery({
    queryKey: ['tarot-decks'],
    queryFn: tarotApi.decks,
  });

  const drawMut = useMutation({
    mutationFn: (spread_type: string) => tarotApi.draw({
      spread_type,
      seed: selectedLeadId ? `lead_${selectedLeadId}_${Date.now()}` : undefined,
    }),
    onSuccess: (res) => {
      setDrawn(res.cards);
      setSavedReadingId(null);
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
        lead_id: selectedLeadId || undefined,
        generate_interpretation: true,
      }),
    onSuccess: (res) => {
      toast.success('Leitura salva');
      setSavedReadingId(res.id);
      setSavedInterpretation(res.interpretation);
      qc.invalidateQueries({ queryKey: ['tarot-history'] });
    },
    onError: handleApiError('Erro ao salvar'),
  });

  const sendMut = useMutation({
    mutationFn: (id: number) => tarotApi.sendReading(id),
    onSuccess: () => {
      toast.success('Leitura enviada pro lead');
      qc.invalidateQueries({ queryKey: ['tarot-history'] });
    },
    onError: handleApiError('Erro ao enviar'),
  });

  const regenMut = useMutation({
    mutationFn: (id: number) => tarotApi.regenerate(id),
    onSuccess: (res) => {
      setSavedInterpretation(res.interpretation);
      toast.success('Interpretação regenerada');
      qc.invalidateQueries({ queryKey: ['tarot-history'] });
    },
    onError: handleApiError('Erro ao regenerar'),
  });

  const spreads = decksData?.spreads ?? [];

  return (
    <div className="p-10 max-w-7xl mx-auto">
      <div className="flex items-start justify-between mb-8">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-2xl bg-accent-amethyst/10 flex items-center justify-center">
              <Wand2 className="w-5 h-5 text-accent-amethyst" />
            </div>
            <h1 className="text-3xl font-black tracking-tight">Tarot Virtual</h1>
          </div>
          <p className="text-secondary text-sm font-medium">
            Tire cartas, gere interpretação com IA, mande pro lead.
          </p>
        </div>
        <button
          onClick={() => setHistoryOpen(true)}
          className="flex items-center gap-2 px-4 py-2.5 bg-bg-surface border border-border hover:border-accent-amethyst/30 rounded-xl text-xs font-bold"
        >
          <History className="w-3.5 h-3.5" />
          Histórico
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-6">
        <LeadPicker selectedId={selectedLeadId} onSelect={setSelectedLeadId} />

        <div className="space-y-6">
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

          <div className="text-center">
            <button
              onClick={() => drawMut.mutate(selectedSpread)}
              disabled={drawMut.isPending}
              className="px-8 py-4 bg-gradient-to-r from-accent-amethyst to-purple-600 hover:scale-105 disabled:opacity-30 text-white rounded-2xl font-black uppercase tracking-widest text-sm shadow-2xl flex items-center gap-3 mx-auto"
            >
              <Shuffle className="w-5 h-5" />
              {drawMut.isPending ? 'Embaralhando...' : 'Tirar cartas'}
            </button>
          </div>

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

              <div className="bg-bg-surface border border-border rounded-3xl p-6 space-y-4">
                {savedInterpretation ? (
                  <>
                    <div className="flex items-center justify-between">
                      <h3 className="text-sm font-black flex items-center gap-2">
                        <Sparkles className="w-4 h-4 text-accent-amethyst" />
                        Interpretação IA
                      </h3>
                      <div className="flex gap-2">
                        <button
                          onClick={() => savedReadingId && regenMut.mutate(savedReadingId)}
                          disabled={!savedReadingId || regenMut.isPending}
                          className="text-[11px] px-3 py-1.5 bg-bg-primary border border-border hover:border-accent-amethyst/30 rounded-lg flex items-center gap-1.5 font-bold"
                        >
                          <RefreshCw className={`w-3 h-3 ${regenMut.isPending ? 'animate-spin' : ''}`} />
                          Regen
                        </button>
                        {selectedLeadId && savedReadingId && (
                          <button
                            onClick={() => sendMut.mutate(savedReadingId)}
                            disabled={sendMut.isPending}
                            className="text-[11px] px-3 py-1.5 bg-accent-amethyst hover:bg-accent-amethyst/90 text-white rounded-lg flex items-center gap-1.5 font-bold"
                          >
                            <Send className="w-3 h-3" />
                            {sendMut.isPending ? 'Enviando…' : 'Enviar pro lead'}
                          </button>
                        )}
                      </div>
                    </div>
                    <div className="prose prose-sm prose-invert text-primary whitespace-pre-wrap leading-relaxed">
                      {savedInterpretation}
                    </div>
                    {!selectedLeadId && (
                      <p className="text-[11px] text-amber-400">
                        Tiragem não vinculada — selecione um lead à esquerda pra mandar pro WhatsApp dele.
                      </p>
                    )}
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
      </div>

      {historyOpen && (
        <HistoryDrawer
          leadId={selectedLeadId}
          onClose={() => setHistoryOpen(false)}
          onSend={(id) => sendMut.mutate(id)}
        />
      )}
    </div>
  );
}

function LeadPicker({
  selectedId, onSelect,
}: {
  selectedId: number | null;
  onSelect: (id: number | null) => void;
}) {
  const [search, setSearch] = useState('');
  const { data, isLoading } = useQuery({
    queryKey: ['tarot-leads-picker', search],
    queryFn: () => inboxApi.getLeads({ search: search || undefined, limit: 30 }),
  });
  const items = (data?.items ?? []) as LeadPreview[];

  return (
    <aside className="bg-bg-surface border border-border rounded-3xl p-4 space-y-3 self-start sticky top-6">
      <h3 className="text-[10px] font-black uppercase tracking-widest text-secondary px-1">
        Lead (opcional)
      </h3>
      <div className="flex items-center gap-2 bg-bg-primary border border-border rounded-xl px-3 py-2">
        <Search className="w-3.5 h-3.5 text-secondary" />
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Buscar…"
          className="flex-1 bg-transparent text-xs outline-none"
        />
      </div>

      <button
        onClick={() => onSelect(null)}
        className={`w-full text-left px-3 py-2 rounded-xl text-xs ${
          selectedId === null
            ? 'bg-accent-amethyst/10 border border-accent-amethyst/30 font-bold'
            : 'hover:bg-bg-primary border border-transparent text-secondary'
        }`}
      >
        Sem lead vinculado
      </button>

      <div className="space-y-1 max-h-[55vh] overflow-y-auto">
        {isLoading ? (
          <div className="text-center text-secondary text-xs py-3">Carregando…</div>
        ) : items.length === 0 ? (
          <div className="text-center text-secondary text-xs py-3">Nenhum lead</div>
        ) : (
          items.map((l) => (
            <button
              key={l.id}
              onClick={() => onSelect(l.id)}
              className={`w-full text-left px-3 py-2 rounded-xl transition-all ${
                selectedId === l.id
                  ? 'bg-accent-amethyst/10 border border-accent-amethyst/30'
                  : 'hover:bg-bg-primary border border-transparent'
              }`}
            >
              <div className="text-xs font-bold truncate">{l.nome || l.telefone}</div>
              <div className="text-[10px] text-secondary truncate">{l.telefone}</div>
            </button>
          ))
        )}
      </div>
    </aside>
  );
}

function HistoryDrawer({
  leadId, onClose, onSend,
}: {
  leadId: number | null;
  onClose: () => void;
  onSend: (id: number) => void;
}) {
  const qc = useQueryClient();
  const [scope, setScope] = useState<'lead' | 'all'>(leadId ? 'lead' : 'all');
  useEffect(() => { if (!leadId) setScope('all'); }, [leadId]);

  const { data, isLoading } = useQuery({
    queryKey: ['tarot-history', scope === 'lead' ? leadId : 'all'],
    queryFn: () =>
      tarotApi.listReadings(
        scope === 'lead' && leadId ? { lead_id: leadId, limit: 50 } : { limit: 50 },
      ),
  });

  const deleteMut = useMutation({
    mutationFn: (id: number) => tarotApi.deleteReading(id),
    onSuccess: () => {
      toast.success('Leitura removida');
      qc.invalidateQueries({ queryKey: ['tarot-history'] });
    },
    onError: handleApiError('Erro ao remover'),
  });

  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex justify-end" onClick={onClose}>
      <div
        className="w-full max-w-md bg-bg-surface border-l border-border h-full overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-5 border-b border-border flex items-center justify-between sticky top-0 bg-bg-surface z-10">
          <h2 className="font-black tracking-tight">Histórico de tiragens</h2>
          <button onClick={onClose} className="text-secondary hover:text-primary text-xl">×</button>
        </div>

        {leadId && (
          <div className="p-4 flex gap-2 border-b border-border">
            <button
              onClick={() => setScope('lead')}
              className={`flex-1 px-3 py-1.5 text-[10px] font-black uppercase tracking-widest rounded-lg ${
                scope === 'lead' ? 'bg-accent-amethyst text-white' : 'bg-bg-primary text-secondary'
              }`}
            >
              Apenas deste lead
            </button>
            <button
              onClick={() => setScope('all')}
              className={`flex-1 px-3 py-1.5 text-[10px] font-black uppercase tracking-widest rounded-lg ${
                scope === 'all' ? 'bg-accent-amethyst text-white' : 'bg-bg-primary text-secondary'
              }`}
            >
              Todos
            </button>
          </div>
        )}

        <div className="p-4 space-y-3">
          {isLoading ? (
            <div className="text-center text-secondary text-sm py-6">Carregando…</div>
          ) : (data?.readings ?? []).length === 0 ? (
            <div className="text-center text-secondary text-sm py-6">Nenhuma leitura.</div>
          ) : (
            (data?.readings ?? []).map((r: TarotReading) => (
              <div key={r.id} className="bg-bg-primary border border-border rounded-2xl p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="text-[11px] font-bold">
                    {r.spread_type} · {r.cards.length} carta{r.cards.length > 1 ? 's' : ''}
                  </div>
                  <div className="text-[10px] text-secondary">
                    {new Date(r.created_at).toLocaleString('pt-BR')}
                  </div>
                </div>
                {r.question && (
                  <div className="text-[11px] text-secondary italic">"{r.question}"</div>
                )}
                <div className="flex flex-wrap gap-1.5">
                  {r.cards.map((c, i) => (
                    <span
                      key={i}
                      className="text-[10px] bg-bg-surface border border-border px-1.5 py-0.5 rounded font-bold"
                    >
                      {c.name}
                      {c.reversed && ' (inv)'}
                    </span>
                  ))}
                </div>
                {r.interpretation && (
                  <p className="text-[11px] text-secondary line-clamp-3 leading-relaxed">
                    {r.interpretation}
                  </p>
                )}
                <div className="flex items-center justify-between pt-1">
                  <div className="text-[10px] text-secondary">
                    {r.lead_id ? `Lead #${r.lead_id}` : 'Sem lead'}
                    {r.sent_to_lead && (
                      <span className="ml-2 inline-flex items-center gap-0.5 text-emerald-400">
                        <Check className="w-2.5 h-2.5" />
                        Enviada
                      </span>
                    )}
                  </div>
                  <div className="flex gap-1.5">
                    {r.lead_id && !r.sent_to_lead && (
                      <button
                        onClick={() => onSend(r.id)}
                        title="Enviar pro lead"
                        className="p-1.5 rounded-lg bg-bg-surface border border-border hover:border-accent-amethyst/30 text-accent-amethyst"
                      >
                        <Send className="w-3 h-3" />
                      </button>
                    )}
                    <button
                      onClick={() => {
                        if (confirm('Remover esta tiragem?')) deleteMut.mutate(r.id);
                      }}
                      className="p-1.5 rounded-lg bg-bg-surface border border-border hover:border-rose-400/30 text-secondary hover:text-rose-400"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
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
