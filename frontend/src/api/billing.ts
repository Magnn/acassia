import { api } from './client';

export interface BillingData {
  plan_labels: Record<string, string>;
  current_status: string | null;
  stripe_configured: boolean;
}

export const billingApi = {
  getPlans: () => api.get<BillingData>('/saas/billing/plans'),
  startCheckout: (plan: string) => api.post(`/saas/billing/checkout/${plan}`),
  openPortal: () => api.post<{ url: string }>('/saas/billing/portal'),
};
