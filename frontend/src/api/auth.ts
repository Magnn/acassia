import { api } from './client';

export interface UserInfo {
  id: number;
  email: string;
  name?: string | null;
  tenant_id: string;
  role: 'admin' | 'user';
  is_verified?: boolean;
  totp_enabled?: boolean;
  // Impersonate (Frente 1.2)
  impersonating?: boolean;
  impersonator?: {
    id: number;
    email: string;
    name?: string | null;
  };
}

export const authApi = {
  me: () => api.get<UserInfo>('/saas/me'),
};
