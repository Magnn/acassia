import { api } from './client';

export interface QuickReply {
  id: number;
  title: string;
  body: string;
  category: string | null;
  shortcut_number: number | null;
  usage_count: number;
  created_at: string;
  updated_at: string | null;
}

export interface Suggestion {
  text: string;
  tone: string;
}

export const composeApi = {
  list: () => api.get<{ quick_replies: QuickReply[] }>('/saas/quick-replies'),

  create: (payload: {
    title: string;
    body: string;
    category?: string;
    shortcut_number?: number | null;
  }) =>
    api.post<{ ok: boolean; quick_reply: QuickReply }>(
      '/saas/quick-replies', payload,
    ),

  update: (id: number, patch: Partial<{
    title: string;
    body: string;
    category: string;
    shortcut_number: number | null;
  }>) =>
    api.patch<{ ok: boolean; quick_reply: QuickReply }>(
      `/saas/quick-replies/${id}`, patch,
    ),

  remove: (id: number) =>
    api.del<{ ok: boolean }>(`/saas/quick-replies/${id}`),

  render: (id: number, leadId?: number) =>
    api.post<{ ok: boolean; text: string }>(
      `/saas/quick-replies/${id}/render`,
      { lead_id: leadId },
    ),

  suggestions: (leadId: number, force = false) =>
    api.post<{ ok: boolean; suggestions: Suggestion[]; cached: boolean }>(
      `/saas/inbox/${leadId}/ai-suggestions`,
      { force },
    ),
};
