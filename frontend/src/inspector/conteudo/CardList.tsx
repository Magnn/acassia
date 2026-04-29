import { ChevronDown, ChevronUp, Plus, X } from 'lucide-react';
import { Field, NumberInput, TextArea, TextInput } from '../fields';
import MediaUpload from './MediaUpload';
import {
  type Card,
  type CardKind,
  KIND_META,
  MAX_CARDS,
  defaultCardForKind,
  isMedia,
} from './types';

interface Props {
  cards: Card[];
  onChange: (next: Card[]) => void;
}

const ALL_KINDS: CardKind[] = ['text', 'image', 'audio', 'video', 'document', 'delay'];

export default function CardList({ cards, onChange }: Props) {
  const update = (i: number, c: Card) => {
    const next = cards.slice();
    next[i] = c;
    onChange(next);
  };
  const remove = (i: number) => {
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

  return (
    <div className="space-y-3">
      <ol className="space-y-2">
        {cards.map((c, i) => {
          const Meta = KIND_META[c.type];
          return (
            <li
              key={i}
              className="rounded border border-cigana-border bg-cigana-bg p-2"
            >
              <div className="flex items-center justify-between mb-2 text-[11px] uppercase tracking-wide text-slate-400">
                <span className="flex items-center gap-1.5">
                  <Meta.Icon className="w-3.5 h-3.5" />
                  <span>{i + 1}. {Meta.label}</span>
                </span>
                <div className="flex items-center gap-0.5">
                  <button
                    type="button"
                    onClick={() => move(i, -1)}
                    disabled={i === 0}
                    className="p-1 rounded hover:text-slate-200 hover:bg-cigana-surface disabled:opacity-30 disabled:hover:bg-transparent"
                    title="Mover acima"
                  >
                    <ChevronUp className="w-3 h-3" />
                  </button>
                  <button
                    type="button"
                    onClick={() => move(i, 1)}
                    disabled={i === cards.length - 1}
                    className="p-1 rounded hover:text-slate-200 hover:bg-cigana-surface disabled:opacity-30 disabled:hover:bg-transparent"
                    title="Mover abaixo"
                  >
                    <ChevronDown className="w-3 h-3" />
                  </button>
                  <button
                    type="button"
                    onClick={() => remove(i)}
                    className="p-1 rounded hover:text-red-400 hover:bg-cigana-surface"
                    title="Remover"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
              </div>
              <CardEditor card={c} onChange={(c2) => update(i, c2)} />
            </li>
          );
        })}
      </ol>

      {cards.length < MAX_CARDS ? (
        <div className="grid grid-cols-3 gap-1">
          {ALL_KINDS.map((k) => {
            const Meta = KIND_META[k];
            return (
              <button
                key={k}
                type="button"
                onClick={() => add(k)}
                className="flex items-center justify-center gap-1 text-xs px-2 py-1.5 rounded border border-cigana-border bg-cigana-bg hover:border-cigana-purple hover:text-slate-100"
                title={`Adicionar card de ${Meta.label}`}
              >
                <Meta.Icon className="w-3.5 h-3.5" />
                <span>{Meta.label}</span>
              </button>
            );
          })}
        </div>
      ) : (
        <p className="text-[11px] text-slate-500 flex items-center gap-1">
          <Plus className="w-3 h-3 opacity-50" />
          Máximo de {MAX_CARDS} cards por bloco Conteúdo (política WhatsApp).
        </p>
      )}
    </div>
  );
}

function CardEditor({ card, onChange }: { card: Card; onChange: (c: Card) => void }) {
  if (card.type === 'text') {
    return (
      <Field label="Texto">
        <TextArea
          value={card.value}
          onChange={(v) => onChange({ type: 'text', value: v })}
          rows={3}
          placeholder="Mensagem do lead…"
        />
      </Field>
    );
  }
  if (card.type === 'delay') {
    return (
      <Field label="Segundos">
        <NumberInput
          value={card.value}
          min={0}
          max={86400}
          onChange={(v) => onChange({ type: 'delay', value: v === '' ? 0 : v })}
        />
      </Field>
    );
  }
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
