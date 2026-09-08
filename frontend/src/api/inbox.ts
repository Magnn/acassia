import { api } from './client';

export interface LeadPreview {
  id: number;
  telefone: string;
  nome: string;
  node_atual: string;
  convertido: boolean;
  bot_pausado: boolean;
  opt_out: boolean;
  ultima_msg: string;
  ultima_em: string | null;
  ultima_remetente?: string | null;
  score_value?: number;
  score_band?: 'hot' | 'warm' | 'cold';
  tags?: string[];
  spiritual_category?: string | null;
  spiritual_urgency?: 'low' | 'med' | 'high' | null;
  is_urgent?: boolean;
  urgent_reason?: string | null;
  is_starred?: boolean;
  is_archived?: boolean;
  is_blocked?: boolean;
  metadata_json?: Record<string, any>;
}

export type SpiritualCategory =
  | 'amor' | 'dinheiro' | 'saude' | 'carreira'
  | 'familia' | 'espiritual' | 'decisao' | 'luto';

export interface LeadMessage {
  id: number;
  texto: string;
  origem: string;
  timestamp: string | null;
  media_url?: string;
  media_type?: string;
  wamid?: string | null;
  delivery_status?: 'sent' | 'delivered' | 'read' | 'failed' | null;
  delivery_status_at?: string | null;
}

export interface LeadDetail {
  id: number;
  telefone: string;
  nome: string;
  bot_pausado: boolean;
  node_atual: string;
}

export interface ConversationData {
  lead: LeadDetail;
  messages: LeadMessage[];
}

export interface LeadAction {
  ok: boolean;
  message?: string;
}

export interface InboxListResp {
  items: LeadPreview[];
  filtro: string;
  total: number;
  sort: string;
  score_band: string | null;
}

export const inboxApi = {
  getLeads: (params: {
    filtro?: string;
    score_band?: string;
    spiritual_category?: string;
    search?: string;
    sort?: 'recency' | 'score' | 'name';
    limit?: number;
  } = {}) => {
    const q = new URLSearchParams();
    if (params.filtro) q.set('filtro', params.filtro);
    if (params.score_band) q.set('score_band', params.score_band);
    if (params.spiritual_category) q.set('spiritual_category', params.spiritual_category);
    if (params.search) q.set('search', params.search);
    if (params.sort) q.set('sort', params.sort);
    if (params.limit) q.set('limit', String(params.limit));
    const qs = q.toString();
    return api.get<InboxListResp>(`/saas/inbox/data${qs ? '?' + qs : ''}`);
  },

  refreshLeadScore: (leadId: number) =>
    api.post<{
      ok: boolean;
      score_value: number;
      score_band: string;
      components: Record<string, number>;
    }>(`/saas/inbox/${leadId}/score/refresh`),

  getConversation: (leadId: number) =>
    api.get<ConversationData>(`/saas/inbox/${leadId}/data`),

  toggleTakeover: (leadId: number) =>
    api.post<{ status: string; bot_pausado: boolean }>(
      `/saas/inbox/${leadId}/takeover/data`,
    ),

  contextAction: (
    leadId: number,
    action: 'toggle_star' | 'toggle_archive' | 'toggle_block' | 'mark_unread',
  ) =>
    api.post<{
      ok: boolean;
      lead_id: number;
      is_starred: boolean;
      is_archived: boolean;
      is_blocked: boolean;
      tags: string[];
      bot_pausado: boolean;
    }>(`/saas/inbox/${leadId}/action`, { action }),

  // Ações expostas pelo motor (app.py) — texto livre para tarólogo intervir.
  sendMessage: (leadId: number, text: string) =>
    api.post<LeadAction>(`/api/leads/${leadId}/send`, { text }),

  pauseBot: (leadId: number) =>
    api.post<LeadAction>(`/api/leads/${leadId}/pause`),

  resumeLastUser: (leadId: number) =>
    api.post<LeadAction>(`/api/leads/${leadId}/resume-last-user`),

  resendCurrentBlock: (leadId: number) =>
    api.post<LeadAction>(`/api/leads/${leadId}/resend-current-block`),

  advanceNode: (leadId: number, target?: string) =>
    api.post<LeadAction>(`/api/leads/${leadId}/advance-node`, { target }),
};
