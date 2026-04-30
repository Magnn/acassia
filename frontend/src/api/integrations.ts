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
  webhook_path: string | null;
  status: 'pending' | 'active' | 'failed';
  last_verified_at: string | null;
  last_error: string | null;
  subscribed_at: string | null;
  subscribe_error: string | null;
  first_inbound_at: string | null;
  last_inbound_at: string | null;
  inbound_count: number;
  created_at: string;
  updated_at: string | null;
}

export interface WaIntegrationStatus {
  binding: WaBinding | null;
  variables: Record<string, unknown>;
  secrets_set: string[];
  webhook_url: string;
  webhook_url_global?: string;
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
  webhook_url_global?: string;
  webhook_path?: string | null;
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

    rotateWebhookPath: () =>
      api.post<{ ok: boolean; webhook_path: string; webhook_url: string }>(
        '/saas/integrations/whatsapp/rotate-webhook-path',
        {},
      ),

    subscribe: () =>
      api.post<{ ok: boolean; binding: WaBinding }>(
        '/saas/integrations/whatsapp/subscribe', {},
      ),

    testSend: (payload: { to: string; body?: string }) =>
      api.post<{
        ok: boolean;
        message_id?: string;
        to?: string;
        error?: string;
        graph_error?: { message?: string; code?: number };
      }>('/saas/integrations/whatsapp/test-send', payload),

    inboundStats: () =>
      api.get<{
        binding_status: string;
        inbound_count_total: number;
        first_inbound_at: string | null;
        last_inbound_at: string | null;
        rate_limiter: {
          tokens_remaining: number;
          burst_capacity: number;
          rate_per_min: number;
        };
        events_last_24h: Record<string, number>;
      }>('/saas/integrations/whatsapp/inbound-stats'),

    inboundLogs: (params: { limit?: number; event_type?: string } = {}) => {
      const q = new URLSearchParams();
      if (params.limit) q.set('limit', String(params.limit));
      if (params.event_type) q.set('event_type', params.event_type);
      const qs = q.toString();
      return api.get<{
        logs: {
          id: number;
          event_type: string;
          message: string | null;
          phone_number_id: string | null;
          tenant_id: string | null;
          created_at: string;
        }[];
      }>(`/saas/integrations/whatsapp/inbound-logs${qs ? '?' + qs : ''}`);
    },
  },
};
