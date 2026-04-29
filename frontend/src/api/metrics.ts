import { api } from './client';

export interface KpiData {
  total_leads: number;
  leads_7d: number;
  leads_30d: number;
  convertidos: number;
  ativas: number;
  pausadas: number;
  opt_out: number;
  conversion_rate: number;
  node_distribution: { node: string; count: number }[];
}

export const metricsApi = {
  get: () => api.get<KpiData>('/saas/metrics/data'),
};
