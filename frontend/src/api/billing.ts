import { api } from './client';

export interface BillingData {
  plan_labels: Record<string, string>;
  current_status: string | null;
  current_plan?: string;
  current_source?: string;
  stripe_configured: boolean;
}

interface CheckoutResponse {
  ok: boolean;
  url: string;
  error?: string;
  session_id?: string;
}

export interface BillingState {
  effective_plan: string;
  effective_label: string;
  effective_source: 'override' | 'stripe' | 'trial' | 'free';
  effective_price_brl: number;
  stripe_configured: boolean;
  billing: {
    plan: string | null;
    billing_period: 'monthly' | 'annual' | null;
    status: string | null;
    current_period_end: string | null;
    trial_end: string | null;
    cancel_at_period_end: boolean;
    canceled_at: string | null;
    pending_plan: string | null;
    pending_billing_period: string | null;
    pending_effective_at: string | null;
    mrr_brl: number;
    has_subscription: boolean;
  } | null;
}

export const billingApi = {
  getPlans: () => api.get<BillingData>('/saas/billing/plans'),
  getState: () => api.get<BillingState>('/saas/billing/state'),
  startCheckout: (
    plan: string,
    options: { billing_period?: 'monthly' | 'annual'; coupon?: string } = {},
  ) =>
    api.post<CheckoutResponse>(`/saas/billing/checkout/${plan}`, options),
  openPortal: () => api.post<CheckoutResponse>('/saas/billing/portal'),

  // Self-service (Frente 2.17/2.18)
  upgrade: (plan: string, billing_period: 'monthly' | 'annual' = 'monthly') =>
    api.post<{ ok: boolean; message: string }>('/saas/billing/upgrade', { plan, billing_period }),
  downgrade: (plan: string, billing_period: 'monthly' | 'annual' = 'monthly') =>
    api.post<{ ok: boolean; scheduled_for: string | null; message: string }>(
      '/saas/billing/downgrade',
      { plan, billing_period },
    ),
  cancelPendingDowngrade: () =>
    api.post<{ ok: boolean }>('/saas/billing/cancel-pending'),

  // Cancellation (Frente 2.21)
  submitCancellation: (payload: {
    reason_category?: string;
    reason_text?: string;
    win_back_offered?: string;
    win_back_accepted?: boolean;
  }) =>
    api.post<{
      ok: boolean;
      kept?: boolean;
      cancelled?: boolean;
      access_until?: string;
      message: string;
    }>('/saas/billing/cancellation', payload),
  abortCancellation: () =>
    api.post<{ ok: boolean; message: string }>('/saas/billing/cancellation/abort'),
};
