import { api } from './client';

export interface AuraImage {
  id: number;
  lead_id: number;
  signo: string;
  week_id: string;
  image_url: string;
  prompt: string | null;
  provider: string;
  sent_to_lead: boolean;
  sent_at: string | null;
  created_at: string;
}

export interface AuraStatus {
  available: boolean;
  provider: string | null;
  hint: string;
}

export const auraApi = {
  status: () => api.get<AuraStatus>('/saas/aura/status'),

  getLatest: (leadId: number) =>
    api.get<{ lead_id: number; signo: string | null; current_week: string; aura: AuraImage | null }>(
      `/saas/aura/leads/${leadId}`,
    ),

  generate: (leadId: number, opts: { force?: boolean; mood?: string } = {}) =>
    api.post<{ ok: boolean; cached: boolean; aura: AuraImage }>(
      `/saas/aura/leads/${leadId}/generate`, opts,
    ),

  send: (leadId: number, auraId?: number) =>
    api.post<{ ok: boolean; aura: AuraImage }>(
      `/saas/aura/leads/${leadId}/send`,
      auraId ? { aura_id: auraId } : {},
    ),
};
