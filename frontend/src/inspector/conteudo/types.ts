// Cards do bloco Conteúdo — espelha o formato persistido pelo dashboard.html.

import {
  Clock,
  FileText,
  Image as ImageIcon,
  Mic,
  Type,
  Video,
  type LucideIcon,
} from 'lucide-react';

export type CardKind = 'text' | 'delay' | 'image' | 'audio' | 'video' | 'document';

export interface TextCard {
  _id?: string;
  type: 'text';
  value: string;
}

export interface DelayCard {
  _id?: string;
  type: 'delay';
  value: number;
}

export interface MediaCard {
  _id?: string;
  type: 'image' | 'audio' | 'video' | 'document';
  value: { url: string; caption: string; send_as_voice?: boolean };
}

export type Card = TextCard | DelayCard | MediaCard;

export const MAX_CARDS = 5;

export function isMedia(c: Card): c is MediaCard {
  return c.type === 'image' || c.type === 'audio' || c.type === 'video' || c.type === 'document';
}

let _cardSeq = 0;
export function cardId(): string {
  _cardSeq += 1;
  return `c-${Date.now().toString(36)}-${_cardSeq.toString(36)}`;
}

export function defaultCardForKind(kind: CardKind): Card {
  const _id = cardId();
  if (kind === 'text') return { _id, type: 'text', value: '' };
  if (kind === 'delay') return { _id, type: 'delay', value: 3 };
  return { _id, type: kind, value: { url: '', caption: '' } };
}

export const KIND_META: Record<CardKind, { label: string; Icon: LucideIcon }> = {
  text: { label: 'Texto', Icon: Type },
  image: { label: 'Imagem', Icon: ImageIcon },
  audio: { label: 'Áudio', Icon: Mic },
  video: { label: 'Vídeo', Icon: Video },
  document: { label: 'Documento', Icon: FileText },
  delay: { label: 'Delay', Icon: Clock },
};
