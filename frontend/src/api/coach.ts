import { api } from './client';

export interface CopyVariation {
  text: string;
  style: string;
}

export interface CopyRewrite {
  text: string;
  improvement_reason: string;
}

export interface LeadSummary {
  main_question: string;
  personal_info_collected: string[] | string;
  current_funnel_stage: string;
  sentiment_dominant: string;
  suggested_next_action: string;
}

export interface GeneratedPersona {
  name: string;
  presentation: string;
  greeting_template: string;
  reading_style: string;
  instructions: { do: string[]; dont: string[] };
  tom_descritor: string;
}

export interface FunnelReview {
  overall_score: number;
  strengths: string[];
  opportunities: Array<{ node_id: string; issue: string; suggestion: string }>;
  key_metric_callout: string;
}

export const coachApi = {
  generateCopy: (params: {
    intent: string;
    persona?: string;
    tone?: 'casual' | 'formal' | 'mistico' | 'direto';
    length?: 'curto' | 'medium' | 'longo';
    include_cta?: boolean;
  }) =>
    api.post<{ ok: boolean; variations: CopyVariation[] }>(
      '/saas/coach/copy/generate',
      params,
    ),

  rewriteCopy: (params: {
    original: string;
    target_tone?: string;
    target_length?: string;
    count?: number;
  }) =>
    api.post<{ ok: boolean; rewrites: CopyRewrite[] }>(
      '/saas/coach/copy/rewrite',
      params,
    ),

  leadSummary: (leadId: number) =>
    api.post<{ ok: boolean; summary: LeadSummary; msgs_analyzed: number }>(
      `/saas/coach/lead/${leadId}/summary`,
      {},
    ),

  generatePersona: (params: {
    tom?: string;
    energia?: string;
    emoji_level?: string;
    length?: string;
    specialty?: string;
    name?: string;
  }) =>
    api.post<{ ok: boolean; persona: GeneratedPersona }>(
      '/saas/coach/persona/generate',
      params,
    ),

  funnelReview: (params: {
    flow_id?: number;
    flow_slug?: string;
    period_days?: number;
  }) =>
    api.post<{
      ok: boolean;
      review?: FunnelReview;
      funnel_summary?: {
        conversion_pct: number;
        unique_leads: number;
        high_drop_nodes: string[];
      };
      low_confidence?: boolean;
      message?: string;
    }>('/saas/coach/funnel-review', params),
};
