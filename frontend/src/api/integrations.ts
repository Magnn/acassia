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

export interface WaBinding {
  phone_number_id: string;
  tenant_id: string;
  waba_id: string | null;
  display_phone_number: string | null;
  has_verify_token: boolean;
  has_app_secret: boolean;
  status: 'pending' | 'active' | 'failed';
  last_verified_at: string | null;
  last_error: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface WaIntegrationStatus {
  binding: WaBinding | null;
  variables: Record<string, unknown>;
  secrets_set: string[];
  webhook_url: string;
  graph_api_version: string;
  global_verify_token_set: boolean;
}

export interface WaTestResult {
  ok: boolean;
  display_phone_number?: string;
  verified_name?: string;
  quality_rating?: string;
  error?: unknown;
  http_status?: number;
}

export interface WaSavePayload {
  access_token: string;
  phone_number_id: string;
  waba_id?: string;
  app_secret?: string;
  verify_token?: string;
  provider?: 'meta_cloud' | 'coex' | 'evolution';
  skip_validation?: boolean;
}

export interface WaSaveResult {
  ok: boolean;
  binding: WaBinding;
  verify_token: string;
  webhook_url: string;
  instructions: string[];
}

export const integrationsApi = {
  summary: () => api.get<IntegrationsSummary>('/api/integrations/summary'),

  whatsapp: {
    status: () => api.get<WaIntegrationStatus>('/saas/integrations/whatsapp'),

    test: (payload: { access_token: string; phone_number_id: string }) =>
      api.post<WaTestResult>('/saas/integrations/whatsapp/test', payload),

    save: (payload: WaSavePayload) =>
      api.post<WaSaveResult>('/saas/integrations/whatsapp', payload),

    remove: () => api.del<{ ok: boolean }>('/saas/integrations/whatsapp'),

    rotateVerifyToken: () =>
      api.post<{ ok: boolean; verify_token: string; webhook_url: string }>(
        '/saas/integrations/whatsapp/rotate-verify-token',
        {},
      ),
  },
};
