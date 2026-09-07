import { api } from './client';

export interface SettingsData {
  cadence_str: string;
  whatsapp_phone_id: string;
  whatsapp_waba_id: string;
  whatsapp_configured: boolean;
  subscription_status: string;
  connect_payouts: boolean;
}

export const settingsApi = {
  get: () => api.get<SettingsData>('/saas/settings/data'),

  updateRecovery: (cadenceStr: string) =>
    api.post<{ status: string; cadence: number[] }>(
      '/saas/settings/recovery/data',
      { cadence_minutes: cadenceStr },
    ),
};
