import { api } from './client';

export interface BillingData {
  plan_labels: Record<string, string>;
  current_status: string | null;
  stripe_configured: boolean;
}

interface CheckoutResponse {
  ok: boolean;
  url: string;
  error?: string;
}

export const billingApi = {
  getPlans: () => api.get<BillingData>('/saas/billing/plans'),
  startCheckout: (plan: string) =>
    api.post<CheckoutResponse>(`/saas/billing/checkout/${plan}`),
  openPortal: () => api.post<CheckoutResponse>('/saas/billing/portal'),
};
