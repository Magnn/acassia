import { api } from './client';

export type ProviderMode = 'meta_cloud' | 'coex' | 'evolution';

export interface WhatsAppStatus {
  ok: boolean;
  mode: ProviderMode;
  configured: boolean;
  implemented?: boolean;
  hint?: string | null;
  phone_number_id?: string | null;
  waba_id?: string | null;
  connection_state?: string | null;
}

export interface WhatsAppConfig {
  provider: ProviderMode;
  meta_cloud: {
    phone_number_id: string;
    waba_id: string;
    has_access_token: boolean;
  };
  coex: {
    api_url: string;
    instance: string;
    has_api_key: boolean;
  };
  evolution: {
    server_url: string;
    instance: string;
    has_api_key: boolean;
  };
}

export interface WhatsAppConfigPatch {
  provider?: ProviderMode;
  meta_cloud?: {
    phone_number_id?: string;
    waba_id?: string;
    access_token?: string; // omitir mantém; '' apaga
  };
  coex?: {
    api_url?: string;
    instance?: string;
    api_key?: string;
  };
  evolution?: {
    server_url?: string;
    instance?: string;
    api_key?: string;
  };
}

export const whatsappApi = {
  status: () => api.get<WhatsAppStatus>('/saas/whatsapp/status'),
  getConfig: () => api.get<WhatsAppConfig>('/saas/whatsapp/config'),
  saveConfig: (patch: WhatsAppConfigPatch) =>
    api.put<{ ok: boolean }>('/saas/whatsapp/config', patch),
  test: (to: string) =>
    api.post<{ ok: boolean; message_id?: string; error?: string }>(
      '/saas/whatsapp/test',
      { to },
    ),
  qr: () =>
    api.get<{ ok: boolean; data?: Record<string, unknown>; error?: string }>(
      '/saas/whatsapp/qr',
    ),
};
