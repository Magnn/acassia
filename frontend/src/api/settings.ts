export interface SettingsData {
  cadence_str: string;
  whatsapp_phone_id: string;
  whatsapp_waba_id: string;
  whatsapp_configured: boolean;
  subscription_status: string;
  connect_payouts: boolean;
}

export const settingsApi = {
  get: async (): Promise<SettingsData> => {
    const res = await fetch('/saas/settings/data');
    if (!res.ok) throw new Error('Failed to fetch settings');
    return res.json();
  },

  updateRecovery: async (cadenceStr: string): Promise<{ status: string; cadence: number[] }> => {
    const res = await fetch('/saas/settings/recovery/data', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cadence_minutes: cadenceStr }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Failed to update recovery');
    return data;
  },
};
