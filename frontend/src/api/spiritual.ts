import { api } from './client';

export interface NatalChart {
  sun: { sign: string; deg: number } | null;
  moon: { sign: string; deg: number; approx: boolean } | null;
  asc: { sign: string; deg: number } | null;
  elements: { fogo: number; terra: number; ar: number; agua: number };
}

export interface NatalRow {
  lead_id: number;
  birth_date: string | null;
  birth_time: string | null;
  birth_place: string | null;
  lat: number | null;
  lon: number | null;
  timezone_offset: number;
  chart: NatalChart | null;
  interpretation: string | null;
  interpretation_focus: string | null;
  computed_at: string | null;
  interpreted_at: string | null;
}

export interface NumerologyRow {
  lead_id: number;
  full_name: string | null;
  birth_date: string | null;
  life_path: number | null;
  expression: number | null;
  soul: number | null;
  components: {
    life_path_meaning: string | null;
    expression_meaning: string | null;
    soul_meaning: string | null;
  } | null;
  interpretation: string | null;
  computed_at: string | null;
  interpreted_at: string | null;
}

export interface SpiritualProfile {
  lead: {
    id: number;
    nome: string | null;
    telefone: string;
    birth_date: string | null;
    signo: string | null;
  };
  natal: NatalRow | null;
  numerology: NumerologyRow | null;
}

export const spiritualApi = {
  getProfile: (leadId: number) =>
    api.get<SpiritualProfile>(`/saas/spiritual/leads/${leadId}`),

  computeNatal: (leadId: number, payload: {
    birth_time?: string;
    birth_place?: string;
    lat?: number;
    lon?: number;
    timezone_offset?: number;
  }) =>
    api.post<{ ok: boolean; natal: NatalRow }>(
      `/saas/spiritual/leads/${leadId}/natal`, payload,
    ),

  interpretNatal: (leadId: number, focus: 'geral' | 'amor' | 'carreira' | 'familia' = 'geral') =>
    api.post<{ ok: boolean; interpretation: string; focus: string }>(
      `/saas/spiritual/leads/${leadId}/natal/interpret`, { focus },
    ),

  computeNumerology: (leadId: number, fullName?: string) =>
    api.post<{ ok: boolean; numerology: NumerologyRow }>(
      `/saas/spiritual/leads/${leadId}/numerology`,
      { full_name: fullName },
    ),

  interpretNumerology: (leadId: number) =>
    api.post<{ ok: boolean; interpretation: string }>(
      `/saas/spiritual/leads/${leadId}/numerology/interpret`, {},
    ),

  sendSummary: (leadId: number) =>
    api.post<{ ok: boolean; preview: string }>(
      `/saas/spiritual/leads/${leadId}/send-summary`, {},
    ),

  extractBirthDate: (params: {
    text: string;
    lead_id?: number;
    persist?: boolean;
    prefer_gemini?: boolean;
  }) =>
    api.post<{
      date: string | null;
      year: number | null;
      month: number | null;
      day: number | null;
      confidence: number;
      source: string;
      needs_clarification: boolean;
      clarification_question: string | null;
      parse_error: string | null;
      confirmation_message: string;
      persisted: boolean;
      computed_sign?: string;
    }>('/saas/spiritual/extract-birth-date', params),
};
