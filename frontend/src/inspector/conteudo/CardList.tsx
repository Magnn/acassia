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
        {cards.map((c, i) => (
          <li
            key={i}
            className="rounded border border-cigana-border bg-cigana-bg p-2"
          >
            <div className="flex items-center justify-between mb-2 text-[11px] uppercase tracking-wide text-slate-400">
              <span>
                {KIND_META[c.type].emoji} {i + 1}. {KIND_META[c.type].label}
              </span>
              <div className="flex items-center gap-1">
                <button
                  type="button"
                  onClick={() => move(i, -1)}
                  disabled={i === 0}
                  className="px-1 hover:text-slate-200 disabled:opacity-30"
                  title="Mover acima"
                >
                  ↑
                </button>
                <button
                  type="button"
                  onClick={() => move(i, 1)}
                  disabled={i === cards.length - 1}
                  className="px-1 hover:text-slate-200 disabled:opacity-30"
                  title="Mover abaixo"
                >
                  ↓
                </button>
                <button
                  type="button"
                  onClick={() => remove(i)}
                  className="px-1 hover:text-red-400"
                  title="Remover"
                >
                  ×
                </button>
              </div>
            </div>
            <CardEditor card={c} onChange={(c2) => update(i, c2)} />
          </li>
        ))}
      </ol>

      {cards.length < MAX_CARDS ? (
        <div className="grid grid-cols-3 gap-1">
          {ALL_KINDS.map((k) => (
            <button
              key={k}
              type="button"
              onClick={() => add(k)}
              className="text-xs px-2 py-1 rounded border border-cigana-border bg-cigana-bg hover:border-cigana-purple"
            >
              {KIND_META[k].emoji} {KIND_META[k].label}
            </button>
          ))}
        </div>
      ) : (
        <p className="text-[11px] text-slate-500">
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
