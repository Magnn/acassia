import { api } from './client';

export interface AffiliateMe {
  enrolled: boolean;
  ref_code?: string;
  ref_link?: string;
  pix_key?: string | null;
  pix_key_type?: string | null;
  tier?: 'standard' | 'silver' | 'gold';
  commission_pct?: number;
  total_referrals?: number;
  active_referrals?: number;
  total_earned_brl?: number;
  total_paid_out_brl?: number;
  pending_brl?: number;
  tier_progress?: {
    current: string;
    next_tier: string | null;
    needed_for_next: number | null;
  };
}

export interface ReferralEntry {
  id: number;
  referred_email: string | null;
  signed_up_at: string | null;
  first_payment_at: string | null;
  status: 'signup' | 'trial' | 'paid' | 'churned';
  total_commission_brl: number;
  last_recurrence_at: string | null;
}

export interface PayoutEntry {
  id: number;
  period_yyyymm: number;
  amount_brl: number;
  status: 'pending' | 'paid' | 'failed';
  paid_at: string | null;
  pix_receipt_url: string | null;
  notes: string | null;
}

export const affiliateApi = {
  me: () => api.get<AffiliateMe>('/saas/affiliate/me'),
  enroll: (params: { pix_key?: string; pix_key_type?: string } = {}) =>
    api.post<{ ok: boolean; ref_code: string }>('/saas/affiliate/enroll', params),
  update: (params: { pix_key?: string; pix_key_type?: string }) =>
    api.patch<{ ok: boolean }>('/saas/affiliate/me', params),
  referrals: () =>
    api.get<{ items: ReferralEntry[] }>('/saas/affiliate/referrals'),
  payouts: () =>
    api.get<{ items: PayoutEntry[] }>('/saas/affiliate/payouts'),
};
