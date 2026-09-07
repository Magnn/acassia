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

export interface ExecutivePoint {
  date: string;
  revenue_brl: number;
  ad_spend_brl: number;
  profit_brl: number;
  transactions_count: number;
  refunded_brl: number;
}

export interface ExecutiveKpis {
  ok: boolean;
  revenue_today?: number;
  sales_count_today?: number;
  spend_today?: number;
  tokens_today?: number;
  wa_starts_today?: number;
  avg_ticket?: number;
  conv_pct?: number;
  series?: ExecutivePoint[];
}

export const metricsApi = {
  get: () => api.get<KpiData>('/saas/metrics/data'),
  getExecutive: (days = 7) =>
    api.get<ExecutiveKpis>(`/api/dashboard/kpis?days=${days}`),
};
