import { api } from './client';

// ─── 2FA ─────────────────────────────────────────────────────────────

export interface TwoFAStatus {
  enabled: boolean;
  has_recovery_codes: boolean;
  cookie_present: boolean;
}

export interface TwoFASetupInit {
  qr_data_url: string;
  secret: string;
  uri: string;
  setup_token: string;
}

export interface TwoFASetupConfirm {
  ok: boolean;
  recovery_codes: string[];
  warning: string;
}

// ─── Tenants ─────────────────────────────────────────────────────────

export interface AdminTenantRow {
  tenant_id: string;
  user_id: number;
  email: string;
  name: string | null;
  role: 'admin' | 'user';
  plan: string;
  plan_label: string;
  plan_source: 'override' | 'stripe' | 'trial' | 'free';
  plan_price_brl: number;
  signup_at: string | null;
  last_login_at: string | null;
  is_verified: boolean;
  is_suspended: boolean;
  suspension_reason: string | null;
  is_deleted: boolean;
  trial_ends_at: string | null;
  leads_30d: number;
  msgs_30d: number;
  admin_subrole: string | null;
}

export interface AdminTenantsListResp {
  tenants: AdminTenantRow[];
  total_count: number;
  cursor_next: number | null;
  has_more: boolean;
}

export interface AdminTenantOverview {
  tenant_id: string;
  user: {
    id: number;
    email: string;
    name: string | null;
    role: string;
    is_active: boolean;
    is_verified: boolean;
    phone: string | null;
    timezone: string;
    signup_at: string | null;
    last_login_at: string | null;
    totp_enabled: boolean;
  };
  plan: {
    key: string;
    label: string;
    source: string;
    price_brl: number;
    limits: Record<string, number>;
    features: Record<string, boolean>;
  };
  lifecycle: {
    is_suspended: boolean;
    suspended_at: string | null;
    suspended_by: number | null;
    suspension_reason: string | null;
    is_deleted: boolean;
    deleted_at: string | null;
    trial_ends_at: string | null;
    dunning_status: string | null;
  };
  metrics: {
    leads_total: number;
    leads_30d: number;
    msgs_total: number;
    msgs_30d: number;
  };
  active_override: {
    id: number;
    plan: string;
    reason: string;
    expires_at: string | null;
  } | null;
  active_grants: Array<{
    id: number;
    kind: string;
    amount: number;
    used_amount: number;
    expires_at: string | null;
    reason: string;
  }>;
  health: {
    score: number;
    band: string;
    components: Record<string, unknown>;
  } | null;
  notes_count: number;
}

export interface AdminNote {
  id: number;
  content: string;
  pinned: boolean;
  author_admin_id: number;
  created_at: string;
  updated_at: string | null;
}

// ─── API ─────────────────────────────────────────────────────────────

export interface ListTenantsFilters {
  cursor?: number;
  limit?: number;
  sort?: string;
  search?: string;
  plan?: string;
  status?: 'active' | 'suspended' | 'deleted' | 'all';
  last_login?: '24h' | '7d' | '30d' | '>30d';
}

function buildTenantsQuery(f: ListTenantsFilters): string {
  const params = new URLSearchParams();
  if (f.cursor) params.set('cursor', String(f.cursor));
  if (f.limit) params.set('limit', String(f.limit));
  if (f.sort) params.set('sort', f.sort);
  if (f.search) params.set('search', f.search);
  if (f.plan) params.set('filter[plan]', f.plan);
  if (f.status) params.set('filter[status]', f.status);
  if (f.last_login) params.set('filter[last_login]', f.last_login);
  const q = params.toString();
  return q ? `?${q}` : '';
}

export const adminApi = {
  // 2FA
  twoFAStatus: () => api.get<TwoFAStatus>('/admin/2fa/status'),
  twoFASetupInit: () => api.post<TwoFASetupInit>('/admin/2fa/setup'),
  twoFASetupConfirm: (totp: string, setup_token: string) =>
    api.post<TwoFASetupConfirm>('/admin/2fa/setup/confirm', { totp, setup_token }),
  twoFAChallenge: (totp: string) =>
    api.post<{ ok: boolean; expires_in_s: number }>('/admin/2fa/challenge', { totp }),
  twoFARecover: (code: string) =>
    api.post<{ ok: boolean; remaining_recovery_codes: number }>('/admin/2fa/recover', { code }),
  twoFADisable: (totp: string) =>
    api.post<{ ok: boolean }>('/admin/2fa/disable', { totp }),
  twoFALogout: () => api.post<{ ok: boolean }>('/admin/2fa/logout'),

  // Tenants
  listTenants: (filters: ListTenantsFilters = {}) =>
    api.get<AdminTenantsListResp>(`/api/admin/tenants${buildTenantsQuery(filters)}`),
  tenantOverview: (tenantId: string) =>
    api.get<AdminTenantOverview>(`/api/admin/tenants/${tenantId}/overview`),

  // Notes
  listNotes: (tenantId: string) =>
    api.get<{ notes: AdminNote[] }>(`/api/admin/tenants/${tenantId}/notes`),
  createNote: (tenantId: string, content: string, pinned = false) =>
    api.post<{ id: number; content: string; pinned: boolean; created_at: string }>(
      `/api/admin/tenants/${tenantId}/notes`,
      { content, pinned },
    ),
  updateNote: (tenantId: string, noteId: number, patch: { content?: string; pinned?: boolean }) =>
    api.patch<{ ok: boolean }>(`/api/admin/tenants/${tenantId}/notes/${noteId}`, patch),
  deleteNote: (tenantId: string, noteId: number) =>
    api.del<{ ok: boolean }>(`/api/admin/tenants/${tenantId}/notes/${noteId}`),
};
