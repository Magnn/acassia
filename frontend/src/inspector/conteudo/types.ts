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

export const KIND_META: Record<CardKind, { label: string; Icon: LucideIcon }> = {
  text: { label: 'Texto', Icon: Type },
  image: { label: 'Imagem', Icon: ImageIcon },
  audio: { label: 'Áudio', Icon: Mic },
  video: { label: 'Vídeo', Icon: Video },
  document: { label: 'Documento', Icon: FileText },
  delay: { label: 'Delay', Icon: Clock },
};
