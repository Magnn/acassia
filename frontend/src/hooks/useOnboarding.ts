import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';

export interface Milestone {
  key: string;
  label: string;
  description: string;
  order: number;
  completed: boolean;
}

export interface OnboardingProgress {
  milestones: Milestone[];
  total: number;
  completed_count: number;
  pct: number;
  next_suggested: { key: string; label: string; description: string } | null;
  all_done: boolean;
}

export function useOnboarding() {
  return useQuery({
    queryKey: ['me', 'onboarding'],
    queryFn: () => api.get<OnboardingProgress>('/saas/me/onboarding'),
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
}
