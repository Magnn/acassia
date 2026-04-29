import { api } from './client';

export interface IntegrationsSummary {
  base_url: string;
  webhooks: { id: string; label: string; path: string; hint: string }[];
  meta: {
    waba_configured: boolean;
    phone_number_configured: boolean;
    token_configured: boolean;
    verify_token_configured: boolean;
  };
  redis_inbound: {
    configured: boolean;
    ready: boolean;
    queue_key: string | null;
    depth: number | null;
  };
  docs: Record<string, string>;
}

export const integrationsApi = {
  summary: () => api.get<IntegrationsSummary>('/api/integrations/summary'),
};
