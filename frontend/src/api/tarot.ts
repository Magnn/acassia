import { api } from './client';

export interface TarotDeck {
  id: string;
  name: string;
  is_default: boolean;
  tenant_id: string | null;
  card_count: number;
}

export interface TarotSpread {
  key: string;
  name: string;
  positions: string[];
}

export interface TarotCardDraw {
  position: string;
  card_id: string;
  name: string;
  arcana: string;
  reversed: boolean;
  meaning: string;
  keywords: string[];
  image_url: string | null;
}

export interface TarotDraw {
  spread_type: string;
  spread_name: string;
  deck_id: string;
  cards: TarotCardDraw[];
}

export interface TarotReading {
  id: number;
  lead_id: number | null;
  spread_type: string;
  deck_id: string;
  cards: TarotCardDraw[];
  question: string | null;
  interpretation: string | null;
  sent_to_lead: boolean;
  sent_at?: string | null;
  created_at: string;
}

export const tarotApi = {
  decks: () =>
    api.get<{ decks: TarotDeck[]; spreads: TarotSpread[] }>('/saas/tarot/decks'),

  draw: (params: {
    spread_type: string;
    deck_id?: string;
    seed?: string;
    reversal_chance?: number;
  }) => api.post<TarotDraw>('/saas/tarot/draw', params),

  saveReading: (params: {
    spread_type: string;
    deck_id?: string;
    cards: TarotCardDraw[];
    lead_id?: number;
    question?: string;
    generate_interpretation?: boolean;
  }) =>
    api.post<{
      ok: boolean;
      id: number;
      interpretation: string | null;
      created_at: string;
    }>('/saas/tarot/readings', params),

  listReadings: (params: { lead_id?: number; limit?: number } = {}) => {
    const q = new URLSearchParams();
    if (params.lead_id) q.set('lead_id', String(params.lead_id));
    if (params.limit) q.set('limit', String(params.limit));
    const qs = q.toString();
    return api.get<{ readings: TarotReading[] }>(
      `/saas/tarot/readings${qs ? '?' + qs : ''}`,
    );
  },

  getReading: (id: number) => api.get<TarotReading>(`/saas/tarot/readings/${id}`),

  sendReading: (id: number) =>
    api.post<{ ok: boolean; preview: string }>(
      `/saas/tarot/readings/${id}/send`, {},
    ),

  regenerate: (id: number) =>
    api.post<{ ok: boolean; interpretation: string }>(
      `/saas/tarot/readings/${id}/regenerate`, {},
    ),

  deleteReading: (id: number) =>
    api.del<{ ok: boolean }>(`/saas/tarot/readings/${id}`),
};
