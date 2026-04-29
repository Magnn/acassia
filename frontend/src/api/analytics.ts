import { api } from './client';

export interface FunnelStep {
  node_id: string;
  entered: number;
  drop: number;
  drop_pct: number;
  exit_reasons: Record<string, number>;
  median_time_s: number | null;
  is_high_drop: boolean;
}

export interface FunnelResp {
  flow_id: number | null;
  flow_slug: string | null;
  period_days: number;
  score_band_filter: string | null;
  total_runs: number;
  unique_leads: number;
  low_confidence: boolean;
  overall_conversion_pct: number;
  steps: FunnelStep[];
}

export interface FlowSummary {
  flow_id: number | null;
  flow_slug: string | null;
  visits: number;
  unique_leads: number;
}

export interface RecoverySuggestion {
  id: number;
  telefone: string;
  nome: string | null;
  score_value: number;
  score_band: string;
  node_atual: string;
  last_msg_at: string | null;
  days_inactive: number;
}

export const analyticsApi = {
  funnel: (params: {
    flow_id?: number;
    flow_slug?: string;
    period_days?: number;
    score_band?: 'hot' | 'warm' | 'cold';
  }) => {
    const q = new URLSearchParams();
    if (params.flow_id) q.set('flow_id', String(params.flow_id));
    if (params.flow_slug) q.set('flow_slug', params.flow_slug);
    if (params.period_days) q.set('period_days', String(params.period_days));
    if (params.score_band) q.set('score_band', params.score_band);
    return api.get<FunnelResp>(`/saas/analytics/funnel?${q.toString()}`);
  },

  flows: (period_days = 30) =>
    api.get<{ flows: FlowSummary[]; period_days: number }>(
      `/saas/analytics/flows?period_days=${period_days}`,
    ),

  leadsByScore: () =>
    api.get<{
      distribution: { hot: number; warm: number; cold: number };
      total: number;
    }>('/saas/analytics/leads/by-score'),

  recoverySuggestions: () =>
    api.get<{
      items: RecoverySuggestion[];
      total: number;
      criteria: { min_days_inactive: number; max_days_inactive: number };
    }>('/saas/analytics/recovery-suggestions'),
};
