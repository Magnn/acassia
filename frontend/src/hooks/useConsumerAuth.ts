import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';

export interface Consumer {
  id: number;
  name: string;
  phone: string;
  email?: string;
  created_at?: string;
}

export function useConsumerAuth() {
  const qc = useQueryClient();
  const token = typeof window !== 'undefined' ? localStorage.getItem('b2c_access_token') : null;

  const { data, isLoading } = useQuery({
    queryKey: ['b2c-auth-me', token],
    queryFn: async () => {
      if (!token) return null;
      try {
        const res = await api.get<{ ok: boolean; consumer: Consumer }>('/api/b2c/auth/me');
        return res.consumer;
      } catch {
        localStorage.removeItem('b2c_access_token');
        return null;
      }
    },
    staleTime: 5 * 60 * 1000,
    retry: false,
  });

  const logout = () => {
    localStorage.removeItem('b2c_access_token');
    qc.setQueryData(['b2c-auth-me', token], null);
    qc.invalidateQueries({ queryKey: ['b2c-vault'] });
    qc.invalidateQueries({ queryKey: ['b2c-appointments'] });
  };

  return {
    consumer: data ?? null,
    isLoading,
    isAuthenticated: Boolean(data),
    logout,
  };
}
