import { api } from './client';

export interface UserInfo {
  id: number;
  email: string;
  name?: string | null;
  tenant_id: string;
  role: 'admin' | 'user';
}

export const authApi = {
  me: () => api.get<UserInfo>('/saas/me'),
};
