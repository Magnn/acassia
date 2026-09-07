import { useState } from 'react';
import { ChevronDown, ChevronUp, GripVertical, Trash2, AlertCircle } from 'lucide-react';
import { Field, TextInput } from '../fields';
import MediaUpload from './MediaUpload';
import {
  type Card,
  type CardKind,
  KIND_META,
  MAX_CARDS,
  cardId,
  defaultCardForKind,
  isMedia,
} from './types';

interface Props {
  cards: Card[];
  onChange: (next: Card[]) => void;
}

const ALL_KINDS: CardKind[] = ['text', 'image', 'audio', 'video', 'document', 'delay'];

/* LAILLA color tokens per type — matching legacy flow-content-type-btn--* and flow-content-card--* */
const TYPE_COLORS: Record<CardKind, { btnText: string; btnIcon: string; strip: string; border: string }> = {
  text:     { btnText: 'text-[#2563eb]', btnIcon: 'text-[#2563eb]', strip: 'bg-[#3b82f6]', border: 'border-[rgba(37,99,235,0.28)]' },
  image:    { btnText: 'text-[#ea580c]', btnIcon: 'text-[#ea580c]', strip: 'bg-[#f97316]', border: 'border-[rgba(234,88,12,0.38)]' },
  audio:    { btnText: 'text-[#9333ea]', btnIcon: 'text-[#9333ea]', strip: 'bg-[#a855f7]', border: 'border-[rgba(147,51,234,0.32)]' },
  video:    { btnText: 'text-[#16a34a]', btnIcon: 'text-[#16a34a]', strip: 'bg-[#22c55e]', border: 'border-[rgba(22,163,74,0.32)]' },
  document: { btnText: 'text-[#1e3a8a]', btnIcon: 'text-[#1e40af]', strip: 'bg-[#3b82f6]', border: 'border-[rgba(59,130,246,0.35)]' },
  delay:    { btnText: 'text-[#db2777]', btnIcon: 'text-[#e11d48]', strip: 'bg-[#ec4899]', border: 'border-[rgba(236,72,153,0.38)]' },
};

/* LAILLA badge labels */
function seqLabelForType(t: string): string {
  const m: Record<string, string> = { text: 'Texto', image: 'Imagem', audio: 'Áudio', video: 'Vídeo', document: 'Documento', delay: 'Delay' };
  return m[t] || t;
}

export default function CardList({ cards, onChange }: Props) {
  const [dragIdx, setDragIdx] = useState<number | null>(null);
  const [dropIdx, setDropIdx] = useState<number | null>(null);

  const update = (i: number, c: Card) => {
    const next = cards.slice();
    next[i] = c;
    onChange(next);
  };
  const remove = (i: number) => {
    const card = cards[i];
    const hasContent = (() => {
      if (card.type === 'text') return !!(card.value && card.value.trim());
      if (card.type === 'delay') return card.value !== 3;
      if (isMedia(card)) return !!(card.value?.url || card.value?.caption);
      return false;
    })();
    if (hasContent && !window.confirm(`Remover este card de ${seqLabelForType(card.type)}? O conteúdo será perdido.`)) {
      return;
    }
    const next = cards.slice();
    next.splice(i, 1);
    onChange(next);
  };
  const move = (i: number, dir: -1 | 1) => {
    const j = i + dir;
    if (j < 0 || j >= cards.length) return;
    const next = cards.slice();
    [next[i], next[j]] = [next[j], next[i]];
    onChange(next);
  };
  const add = (kind: CardKind) => {
    if (cards.length >= MAX_CARDS) return;
    onChange([...cards, defaultCardForKind(kind)]);
  };

  // ── Drag & Drop handlers ──
  const handleDragStart = (e: React.DragEvent, i: number) => {
    setDragIdx(i);
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', String(i));
    // Make the drag image slightly transparent
    if (e.currentTarget instanceof HTMLElement) {
      e.currentTarget.style.opacity = '0.5';
    }
  };

  const handleDragEnd = (e: React.DragEvent) => {
    if (e.currentTarget instanceof HTMLElement) {
      e.currentTarget.style.opacity = '1';
    }
    setDragIdx(null);
    setDropIdx(null);
  };

  const handleDragOver = (e: React.DragEvent, i: number) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    if (dragIdx !== null && dragIdx !== i) {
      setDropIdx(i);
    }
  };

  const handleDragLeave = () => {
    setDropIdx(null);
  };

  const handleDrop = (e: React.DragEvent, targetIdx: number) => {
    e.preventDefault();
    if (dragIdx === null || dragIdx === targetIdx) {
      setDragIdx(null);
      setDropIdx(null);
      return;
    }
    const next = cards.slice();
    const [dragged] = next.splice(dragIdx, 1);
    next.splice(targetIdx, 0, dragged);
    onChange(next);
    setDragIdx(null);
    setDropIdx(null);
  };

  const atMax = cards.length >= MAX_CARDS;

  return (
    <div className="flow-content-builder" style={{ fontFamily: "'Inter', ui-sans-serif, system-ui, sans-serif" }}>
      
      {/* ── Notice: Max cards reached (LAILLA red warning) ── */}
      {atMax && (
        <div className="mb-3 p-4 rounded-[10px] border" style={{ background: '#fef2f2', borderColor: 'rgba(153,27,27,0.12)' }}>
          <div className="flex gap-2.5 items-start">
            <span className="shrink-0 w-[22px] h-[22px] rounded-full bg-[#991b1b] text-white flex items-center justify-center text-[11px]">
              <AlertCircle className="w-3 h-3" />
            </span>
            <div>
              <p className="text-[12px] font-semibold text-[#991b1b] leading-[1.45] mb-2">
                A fim de otimizar a performance e análise de seus blocos de conteúdo, sugerimos as seguintes práticas:
              </p>
              <ul className="text-[11.5px] text-[#7f1d1d] leading-[1.5] pl-4 list-disc mb-2">
                <li>Mantenha no máximo {MAX_CARDS} passos por bloco</li>
                <li>Utilize outro bloco "Conteúdo" para mais passos</li>
              </ul>
              <div className="text-[11.5px] font-semibold text-[#991b1b] leading-[1.45] p-2.5 rounded-lg" style={{ background: 'rgba(254,202,202,0.35)', border: '1px solid rgba(185,28,28,0.22)' }}>
                Atingiu o <strong>{MAX_CARDS} passos</strong> permitidos neste bloco (regras Meta / WhatsApp e métricas). Guarde e use outro bloco "Conteúdo".
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Content Type Buttons — 3×2 grid (LAILLA flow-content-type-grid) ── */}
      <div className="grid grid-cols-3 gap-2 mb-0.5">
        {ALL_KINDS.map((k) => {
          const Meta = KIND_META[k];
          const tc = TYPE_COLORS[k];
          const disabled = atMax;
          return (
            <button
              key={k}
              type="button"
              disabled={disabled}
              onClick={() => add(k)}
              className={[
                "flex flex-col items-center justify-center gap-[5px] px-1.5 py-[11px]",
                "rounded-[10px] border border-[#e8eaee] bg-[#f3f4f6]",
                "text-[11px] font-bold cursor-pointer transition-all",
                !disabled ? "hover:bg-[#eceff2] hover:border-[#dde1e8] hover:shadow-sm hover:-translate-y-px" : "",
                disabled ? "opacity-45 cursor-not-allowed" : "",
                tc.btnText,
              ].join(' ')}
              style={{ boxShadow: '0 1px 0 rgba(255,255,255,0.8) inset' }}
              title={disabled
                ? `Limite de ${MAX_CARDS} passos (WhatsApp / métricas). Adicione outro bloco Conteúdo.`
                : `Adicionar ${Meta.label}`
              }
            >
              <Meta.Icon className={`w-[17px] h-[17px] ${tc.btnIcon}`} strokeWidth={1.8} />
              <span>{Meta.label}</span>
            </button>
          );
        })}
      </div>

      {/* ── Divider "Conteúdos" — LAILLA flow-inspector-conteudo__divider ── */}
      <div className="flex items-center gap-3 mt-4 mb-2.5">
        <div className="flex-1 h-px bg-[#e2e8f0]" />
        <span className="text-[11px] font-semibold text-[#94a3b8] tracking-wide">Conteúdos</span>
        <div className="flex-1 h-px bg-[#e2e8f0]" />
      </div>

      {/* ── Empty state or card list ── */}
      <div className="min-h-0">
        {cards.length === 0 ? (
          <div
            className="flex items-center justify-center w-full my-1 py-[11px] px-4 rounded-full text-[12px] font-semibold text-white text-center tracking-wide"
            style={{
              background: 'linear-gradient(180deg, #3b82f6 0%, #2563eb 100%)',
              boxShadow: '0 1px 3px rgba(37,99,235,0.25)',
              letterSpacing: '0.01em',
            }}
          >
            Nenhum conteúdo foi adicionado.
          </div>
        ) : (
          <div id="flow-content-list" className="flex flex-col gap-[14px] mt-0.5">
            {cards.map((c, i) => {
              const tc = TYPE_COLORS[c.type] || TYPE_COLORS.text;
              const isDragging = dragIdx === i;
              const isDropTarget = dropIdx === i;
              return (
                <div
                  key={c._id || `card-${i}`}
                  onDragOver={(e) => handleDragOver(e, i)}
                  onDragLeave={handleDragLeave}
                  onDrop={(e) => handleDrop(e, i)}
                  className={[
                    `relative rounded-xl border bg-white overflow-hidden shadow-[0_1px_3px_rgba(15,23,42,0.05)] ${tc.border}`,
                    'transition-all duration-200',
                    isDragging ? 'opacity-50 scale-[0.97]' : '',
                    isDropTarget ? 'ring-2 ring-[#7c3aed] ring-offset-1 border-[#7c3aed]' : '',
                  ].join(' ')}
                  style={{ padding: '12px 12px 12px 16px' }}
                >
                  {/* Drop indicator line */}
                  {isDropTarget && dragIdx !== null && dragIdx > i && (
                    <div className="absolute -top-[8px] left-3 right-3 h-[3px] rounded-full bg-[#7c3aed]" />
                  )}
                  {isDropTarget && dragIdx !== null && dragIdx < i && (
                    <div className="absolute -bottom-[8px] left-3 right-3 h-[3px] rounded-full bg-[#7c3aed]" />
                  )}

                  {/* Color strip — LAILLA flow-content-card::before */}
                  <div
                    className={`absolute left-0 top-[6px] bottom-[6px] w-1 rounded-[4px] ${tc.strip}`}
                  />

                  {/* Toolbar — LAILLA flow-content-card__toolbar */}
                  <div className="flex items-center justify-between gap-2 mb-2.5">
                    <div className="flex items-center gap-2 min-w-0">
                      {/* Drag handle */}
                      <span
                        draggable
                        onDragStart={(e) => { e.stopPropagation(); handleDragStart(e, i); }}
                        onDragEnd={handleDragEnd}
                        className="inline-flex items-center justify-center w-7 h-7 rounded-lg text-[#94a3b8] cursor-grab active:cursor-grabbing hover:text-[#64748b] hover:bg-slate-100/60 select-none"
                      >
                        <GripVertical className="w-4 h-4" />
                      </span>
                      {/* Badge: "Texto · 1" */}
                      <span className="text-[10px] font-bold uppercase tracking-[0.06em] text-[#64748b]">
                        {seqLabelForType(c.type)} · {i + 1}
                      </span>
                    </div>
                    {/* Actions */}
                    <div className="flex items-center gap-1">
                      <button
                        type="button"
                        onClick={() => move(i, -1)}
                        disabled={i === 0}
                        className="w-7 h-7 rounded-lg border border-[#e2e8f0] bg-white flex items-center justify-center text-[#64748b] hover:bg-[#f1f5f9] hover:text-[#4338ca] disabled:opacity-30 transition-colors"
                        title="Mover para cima"
                      >
                        <ChevronUp className="w-3.5 h-3.5" />
                      </button>
                      <button
                        type="button"
                        onClick={() => move(i, 1)}
                        disabled={i === cards.length - 1}
                        className="w-7 h-7 rounded-lg border border-[#e2e8f0] bg-white flex items-center justify-center text-[#64748b] hover:bg-[#f1f5f9] hover:text-[#4338ca] disabled:opacity-30 transition-colors"
                        title="Mover para baixo"
                      >
                        <ChevronDown className="w-3.5 h-3.5" />
                      </button>
                      <button
                        type="button"
                        onClick={() => remove(i)}
                        className="w-7 h-7 rounded-lg border border-[#e2e8f0] bg-white flex items-center justify-center text-[#64748b] hover:text-[#e11d48] hover:border-[#fecdd3] hover:bg-[#fff1f2] transition-colors"
                        title="Remover"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>

                  <CardEditor card={c} onChange={(c2) => update(i, c2)} />
                </div>
              );
            })}
          </div>
        )}
      </div>

      {cards.length > 0 && cards.length < MAX_CARDS && (
        <p className="text-[10px] text-[#94a3b8] mt-3 text-center">
          <span className="opacity-60">0–600s · pausa antes do próximo passo</span>
        </p>
      )}
    </div>
  );
}

/* ── Card Editor — renders the body of each content card ── */

function CardEditor({ card, onChange }: { card: Card; onChange: (c: Card) => void }) {
  
  /* TEXT — textarea with variable insertion hint */
  if (card.type === 'text') {
    return (
      <div>
        <textarea
          value={card.value}
          onChange={(e) => onChange({ type: 'text', value: e.target.value })}
          rows={4}
          placeholder="Digite seu texto aqui"
          className="w-full rounded-[10px] border border-[#e2e8f0] bg-[#f1f5f9] px-2.5 py-2 text-[13px] text-slate-800 placeholder:text-slate-400 focus:outline-none focus:border-[#6366f1] focus:ring-[3px] focus:ring-[rgba(99,102,241,0.14)] focus:bg-white transition-colors resize-y min-h-[88px] max-h-[260px] leading-[1.45]"
          style={{ fontFamily: "'Inter', ui-sans-serif, system-ui, sans-serif" }}
        />
        <p className="text-[10px] text-[#94a3b8] mt-1">
          Use <code className="bg-[#f1f5f9] px-1 rounded text-[9px] font-mono">{'{{variavel}}'}</code> para inserir variáveis do tenant.
        </p>
      </div>
    );
  }

  /* DELAY — slider 0-120s with numeric input */
  if (card.type === 'delay') {
    const sec = typeof card.value === 'number' ? card.value : 0;
    const clamped = Math.max(0, Math.min(120, sec));
    const setDelay = (v: number) => onChange({ ...card, type: 'delay', value: Math.max(0, Math.min(120, Math.round(v))) });
    return (
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2">
          <input
            type="number"
            min={0}
            max={120}
            value={Math.round(clamped)}
            onChange={(e) => setDelay(Number(e.target.value))}
            className="w-[70px] rounded-lg border border-[#e2e8f0] bg-[#f1f5f9] px-2 py-1 text-[13px] text-center font-semibold text-[#475569] focus:outline-none focus:border-[#6366f1] focus:ring-[2px] focus:ring-[rgba(99,102,241,0.14)] focus:bg-white"
          />
          <span className="text-[12px] font-medium text-[#94a3b8]">segundos</span>
        </div>
        <input
          type="range"
          min={0}
          max={120}
          step={1}
          value={Math.round(clamped)}
          onChange={(e) => setDelay(Number(e.target.value))}
          className="w-full"
          style={{ accentColor: '#6366f1' }}
        />
        <span className="text-[10px] text-[#94a3b8]">0–120s · pausa antes do próximo passo</span>
      </div>
    );
  }

  /* MEDIA types — upload zone + voice toggle for audio */
  if (isMedia(card)) {
    return (
      <div className="space-y-2">
        <MediaUpload
          kind={card.type}
          url={card.value.url}
          onChange={(url) =>
            onChange({ type: card.type, value: { ...card.value, url } })
          }
        />
        {/* Voice toggle for audio — LAILLA flow-content-card__voice-toggle */}
        {card.type === 'audio' && (
          <VoiceToggle
            checked={card.value.send_as_voice !== false}
            onChange={(checked) =>
              onChange({ type: 'audio', value: { ...card.value, send_as_voice: checked } })
            }
          />
        )}
        <Field label="Legenda (opcional)">
          <TextInput
            value={card.value.caption}
            onChange={(caption) =>
              onChange({ type: card.type, value: { ...card.value, caption } })
            }
            placeholder="Descrição que aparece com a mídia"
          />
        </Field>
      </div>
    );
  }
  return null;
}

/* ── Voice Toggle — LAILLA flow-inspector-conteudo__toggle ── */

function VoiceToggle({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <div className="flex items-center justify-between p-2.5 rounded-lg border border-[#e8ecf1] bg-white/85 mt-1">
      <span className="text-[13px] font-medium text-[#334155]" style={{ fontFamily: "'Inter', ui-sans-serif, system-ui, sans-serif" }}>
        Enviar como áudio gravado?
      </span>
      <label className="relative w-[38px] h-[22px] shrink-0 cursor-pointer">
        <input
          type="checkbox"
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
          className="opacity-0 w-0 h-0 absolute"
        />
        <span
          className="absolute inset-0 rounded-full transition-colors duration-200"
          style={{ background: checked ? 'linear-gradient(135deg, #4f46e5, #6366f1)' : '#cbd5e1' }}
        />
        <span
          className="absolute bottom-[3px] left-[3px] w-4 h-4 rounded-full bg-white transition-transform duration-200"
          style={{
            transform: checked ? 'translateX(16px)' : 'translateX(0)',
            boxShadow: '0 1px 3px rgba(15,23,42,0.2)',
          }}
        />
      </label>
    </div>
  );
}
