import { api } from './client';

export interface TenantVariable {
  key: string;
  value: unknown;
  updated_at: string;
}

export interface TenantSecret {
  key: string;
  masked: string;
  updated_at: string;
}

export const tenantConfigApi = {
  // ── Variables (JSON values, não-sensíveis) ──────────────────────────
  listVariables: async (): Promise<TenantVariable[]> => {
    const data = await api.get<{ ok: boolean; variables: TenantVariable[] }>(
      '/api/flows/tenant/variables',
    );
    return data.variables;
  },
  setVariable: (key: string, value: unknown) =>
    api.post<{ ok: boolean }>('/api/flows/tenant/variables', { key, value }),
  deleteVariable: (key: string) =>
    api.del<{ ok: boolean }>(
      `/api/flows/tenant/variables/${encodeURIComponent(key)}`,
    ),

  // ── Secrets (cifrados, valor nunca volta plaintext) ─────────────────
  listSecrets: async (): Promise<TenantSecret[]> => {
    const data = await api.get<{ ok: boolean; secrets: TenantSecret[] }>(
      '/api/flows/tenant/secrets',
    );
    return data.secrets;
  },
  setSecret: (key: string, value: string) =>
    api.post<{ ok: boolean }>('/api/flows/tenant/secrets', { key, value }),
  deleteSecret: (key: string) =>
    api.del<{ ok: boolean }>(
      `/api/flows/tenant/secrets/${encodeURIComponent(key)}`,
    ),
};
