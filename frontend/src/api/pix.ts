import { api } from './client';

export interface PixPayment {
  id: number;
  status: 'pending' | 'approved' | 'expired' | 'cancelled';
  amount_brl: number;
  description: string | null;
  lead_id: number | null;
  expires_at: string | null;
  paid_at: string | null;
  created_at?: string;
  qr_code_image_url: string | null;
  qr_code_text: string | null;
}

export const pixApi = {
  create: (params: {
    amount_brl: number;
    description?: string;
    lead_id?: number;
    expires_min?: number;
    payer_email?: string;
  }) =>
    api.post<{
      ok: boolean;
      id: number;
      qr_code_image_url: string | null;
      qr_code_text: string | null;
      amount_brl: number;
      expires_at: string | null;
      status: string;
    }>('/saas/pix/create', params),

  get: (id: number) => api.get<PixPayment>(`/saas/pix/${id}`),

  list: (params: { status?: string; lead_id?: number; limit?: number } = {}) => {
    const q = new URLSearchParams();
    if (params.status) q.set('status', params.status);
    if (params.lead_id) q.set('lead_id', String(params.lead_id));
    if (params.limit) q.set('limit', String(params.limit));
    const qs = q.toString();
    return api.get<{ items: PixPayment[] }>(`/saas/pix/${qs ? '?' + qs : ''}`);
  },

  cancel: (id: number) => api.post<{ ok: boolean }>(`/saas/pix/${id}/cancel`),
};
