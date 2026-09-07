import { api } from './client';

export interface LeadNote {
  id: number;
  content: string;
  author_user_id: number | null;
  created_at: string;
  updated_at: string | null;
}

export interface NextActionSuggestion {
  summary: string;
  action: string;
  message: string;
}

export interface LeadProfilePatch {
  nome?: string | null;
  signo?: string | null;
  idade?: number | null;
  cidade?: string | null;
  email?: string | null;
  tags?: string[];
  custom_fields?: Record<string, string | number | boolean>;
}

export const leadContextApi = {
  patchProfile: (leadId: number, patch: LeadProfilePatch) =>
    api.patch<{ ok: boolean; changes?: Record<string, unknown>; no_changes?: boolean }>(
      `/saas/inbox/${leadId}/profile`, patch,
    ),

  listNotes: (leadId: number) =>
    api.get<{ notes: LeadNote[] }>(`/saas/inbox/${leadId}/notes`),

  createNote: (leadId: number, content: string) =>
    api.post<{ ok: boolean; note: LeadNote }>(
      `/saas/inbox/${leadId}/notes`, { content },
    ),

  updateNote: (leadId: number, noteId: number, content: string) =>
    api.patch<{ ok: boolean; note: LeadNote }>(
      `/saas/inbox/${leadId}/notes/${noteId}`, { content },
    ),

  deleteNote: (leadId: number, noteId: number) =>
    api.del<{ ok: boolean }>(`/saas/inbox/${leadId}/notes/${noteId}`),

  nextAction: (leadId: number, force = false) =>
    api.post<{ ok: boolean; suggestion: NextActionSuggestion; cached: boolean }>(
      `/saas/inbox/${leadId}/next-action`, { force },
    ),
};
