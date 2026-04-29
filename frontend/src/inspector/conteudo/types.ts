// Cards do bloco Conteúdo — espelha o formato persistido pelo dashboard.html.

export type CardKind = 'text' | 'delay' | 'image' | 'audio' | 'video' | 'document';

export interface TextCard {
  type: 'text';
  value: string;
}

export interface DelayCard {
  type: 'delay';
  value: number;
}

export interface MediaCard {
  type: 'image' | 'audio' | 'video' | 'document';
  value: { url: string; caption: string };
}

export type Card = TextCard | DelayCard | MediaCard;

export const MAX_CARDS = 5;

export function isMedia(c: Card): c is MediaCard {
  return c.type === 'image' || c.type === 'audio' || c.type === 'video' || c.type === 'document';
}

export function defaultCardForKind(kind: CardKind): Card {
  if (kind === 'text') return { type: 'text', value: '' };
  if (kind === 'delay') return { type: 'delay', value: 3 };
  return { type: kind, value: { url: '', caption: '' } };
}

export const KIND_META: Record<CardKind, { label: string; emoji: string }> = {
  text: { label: 'Texto', emoji: '📝' },
  image: { label: 'Imagem', emoji: '🖼️' },
  audio: { label: 'Áudio', emoji: '🎙️' },
  video: { label: 'Vídeo', emoji: '🎬' },
  document: { label: 'Documento', emoji: '📄' },
  delay: { label: 'Delay', emoji: '⏱️' },
};
