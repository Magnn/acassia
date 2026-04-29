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
}

export interface LeadMessage {
  id: number;
  texto: string;
  origem: string;
  timestamp: string | null;
  media_url?: string;
  media_type?: string;
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

export const inboxApi = {
  getLeads: (filtro = 'todos') =>
    api.get<{ items: LeadPreview[]; filtro: string }>(
      `/saas/inbox/data?filtro=${encodeURIComponent(filtro)}`,
    ),

  getConversation: (leadId: number) =>
    api.get<ConversationData>(`/saas/inbox/${leadId}/data`),

  toggleTakeover: (leadId: number) =>
    api.post<{ status: string; bot_pausado: boolean }>(
      `/saas/inbox/${leadId}/takeover/data`,
    ),

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
