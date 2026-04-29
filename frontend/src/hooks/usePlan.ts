import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';

export interface MyPlan {
  plan: string;
  label: string;
  source: 'override' | 'stripe' | 'trial' | 'free';
  price_brl: number;
  limits: Record<string, number>;
  features: Record<string, boolean>;
}

export interface MyUsageEntry {
  count: number;
  cost_brl_cents: number;
  limit: number;
  unlimited: boolean;
  pct: number;
  remaining: number | null;
}

export interface MyUsage {
  usage: Record<string, MyUsageEntry>;
  tenant_id: string;
}

const PLAN_RANK: Record<string, number> = { free: 0, starter: 1, pro: 2, enterprise: 3 };

export function planRank(plan: string): number {
  return PLAN_RANK[plan] ?? -1;
}

export function isPlanAtLeast(plan: string, minPlan: string): boolean {
  return planRank(plan) >= planRank(minPlan);
}

/** Hook para o plano efetivo do user logado. */
export function useMyPlan() {
  return useQuery({
    queryKey: ['me', 'plan'],
    queryFn: () => api.get<MyPlan>('/saas/me/plan'),
    staleTime: 60_000, // 1 min
  });
}

/** Hook para uso atual do user logado. */
export function useMyUsage() {
  return useQuery({
    queryKey: ['me', 'usage'],
    queryFn: () => api.get<MyUsage>('/saas/me/usage'),
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
}

/** Hook utilitário pra checar feature ligada. */
export function useFeature(feature: string): { enabled: boolean; loading: boolean } {
  const { data, isLoading } = useMyPlan();
  return {
    enabled: data?.features?.[feature] ?? false,
    loading: isLoading,
  };
}
