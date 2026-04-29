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
  get: async (): Promise<KpiData> => {
    const res = await fetch('/saas/metrics/data');
    if (!res.ok) {
      throw new Error(`Failed to fetch metrics: ${res.status}`);
    }
    return res.json();
  },
};
