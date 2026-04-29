import { api } from './client';

export interface VoiceClone {
  id: number;
  name: string | null;
  provider: string;
  provider_voice_id: string;
  status: 'pending' | 'active' | 'failed';
  sample_audio_url: string | null;
  consented_at: string | null;
  created_at: string;
}

export const voiceApi = {
  configured: () => api.get<{ configured: boolean }>('/saas/voice/configured'),
  list: () => api.get<{ clones: VoiceClone[] }>('/saas/voice/clones'),
  enroll: async (form: FormData) => {
    const res = await fetch('/saas/voice/clones', {
      method: 'POST',
      credentials: 'include',
      headers: { Accept: 'application/json' },
      body: form,
    });
    const text = await res.text();
    const data = text ? JSON.parse(text) : null;
    if (!res.ok) {
      const err = new Error(`POST /saas/voice/clones → ${res.status}`) as Error & {
        status?: number;
        body?: unknown;
      };
      err.status = res.status;
      err.body = data;
      throw err;
    }
    return data as {
      ok: boolean;
      id: number;
      name: string;
      provider_voice_id: string;
      status: string;
    };
  },
  delete: (id: number) =>
    api.del<{ ok: boolean }>(`/saas/voice/clones/${id}`),
  synthesize: (cloneId: number, text: string, lead_id?: number) =>
    api.post<{
      ok: boolean;
      generation_id: number;
      audio_url: string;
      chars_count: number;
      size_bytes: number;
    }>(`/saas/voice/clones/${cloneId}/synthesize`, { text, lead_id }),
  testSample: (cloneId: number) =>
    api.post<{ ok: boolean; sample_audio_url: string }>(
      `/saas/voice/clones/${cloneId}/test`,
    ),
};
