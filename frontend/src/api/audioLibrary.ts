import { api } from './client';

export interface AudioLibraryItem {
  id: number;
  title: string;
  category: string | null;
  tags: string[];
  audio_url: string;
  duration_s: number | null;
  uploaded_by: number | null;
  usage_count: number;
  created_at: string;
}

export const audioLibraryApi = {
  list: (params: { category?: string; search?: string } = {}) => {
    const q = new URLSearchParams();
    if (params.category) q.set('category', params.category);
    if (params.search) q.set('search', params.search);
    const qs = q.toString();
    return api.get<{ items: AudioLibraryItem[]; total: number }>(
      `/saas/audio-library${qs ? '?' + qs : ''}`,
    );
  },

  categories: () =>
    api.get<{ categories: { category: string; count: number }[] }>(
      '/saas/audio-library/categories',
    ),

  upload: async (form: FormData) => {
    return api.upload<{ ok: boolean; item: AudioLibraryItem }>('/saas/audio-library', form);
  },

  update: (
    id: number,
    patch: Partial<{ title: string; category: string; tags: string[] }>,
  ) =>
    api.patch<{ ok: boolean; item: AudioLibraryItem }>(
      `/saas/audio-library/${id}`,
      patch,
    ),

  remove: (id: number) =>
    api.del<{ ok: boolean }>(`/saas/audio-library/${id}`),

  send: (id: number, leadId: number) =>
    api.post<{
      ok: boolean;
      audio_url: string;
      title: string;
      usage_count: number;
    }>(`/saas/audio-library/${id}/send`, { lead_id: leadId }),

  suggest: (leadId: number) =>
    api.post<{
      matched_category: string | null;
      lead_spiritual_category: string | null;
      suggestions: AudioLibraryItem[];
    }>(`/saas/audio-library/suggest`, { lead_id: leadId }),
};
