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

  // Impersonate (Frente 1.2)
  startImpersonate: (target_user_id: number, reason: string, totp: string, duration_min = 60) =>
    api.post<{
      ok: boolean;
      session_id: number;
      target: { user_id: number; email: string; name: string | null; tenant_id: string };
      expires_at: string;
      duration_min: number;
      redirect_to: string;
    }>('/api/admin/impersonate', { target_user_id, reason, totp, duration_min }),
  stopImpersonate: () =>
    api.post<{ ok: boolean; redirect_to: string }>('/api/admin/impersonate/stop'),
  activeImpersonation: () =>
    api.get<{
      active: boolean;
      session_id?: number;
      started_at?: string;
      expires_at?: string;
      expires_in_s?: number;
      reason?: string;
      target?: { user_id: number | null; email: string; name: string | null; tenant_id: string };
      admin?: { user_id: number | null; email: string };
    }>('/api/admin/impersonate/active'),

  // Lifecycle (Frente 1.8 / 1.9)
  suspendTenant: (tenantId: string, reason: string) =>
    api.post<{ ok: boolean; suspended_at: string }>(`/api/admin/tenants/${tenantId}/suspend`, { reason }),
  reactivateTenant: (tenantId: string, reason: string) =>
    api.post<{ ok: boolean; reactivated_at: string }>(`/api/admin/tenants/${tenantId}/reactivate`, { reason }),
  deleteTenant: (tenantId: string, confirm_email: string, reason: string) =>
    api.post<{ ok: boolean; deleted_at: string; recovery_window_days: number }>(
      `/api/admin/tenants/${tenantId}/delete`,
      { confirm_email, reason },
    ),
  restoreTenant: (tenantId: string, reason: string) =>
    api.post<{ ok: boolean; restored_at: string }>(`/api/admin/tenants/${tenantId}/restore`, { reason }),

  // Plan overrides (Frente 1.5)
  createPlanOverride: (
    tenantId: string,
    payload: { plan: string; duration_days?: number | null; pauses_stripe?: boolean; reason: string },
  ) =>
    api.post<{
      ok: boolean;
      override: {
        id: number; plan: string; expires_at: string | null;
        starts_at: string; pauses_stripe: boolean; reason: string;
      };
      effective_plan_now: string;
      effective_source: string;
    }>(`/api/admin/tenants/${tenantId}/plan-overrides`, payload),
  revokePlanOverride: (tenantId: string, overrideId: number, reason: string) =>
    api.del<{ ok: boolean }>(`/api/admin/tenants/${tenantId}/plan-overrides/${overrideId}`, { reason }),
  listPlanOverrides: (tenantId: string, includeRevoked = false) =>
    api.get<{
      overrides: Array<{
        id: number; plan: string; reason: string;
        starts_at: string; expires_at: string | null;
        pauses_stripe: boolean;
        revoked_at: string | null; revoked_reason: string | null;
        granted_by_admin_id: number; created_at: string;
      }>;
    }>(`/api/admin/tenants/${tenantId}/plan-overrides${includeRevoked ? '?include=all' : ''}`),

  // Quota grants (Frente 1.6)
  createQuotaGrant: (
    tenantId: string,
    payload: { kind: string; amount: number; duration_days?: number | null; reason: string },
  ) =>
    api.post<{
      ok: boolean;
      grant: { id: number; kind: string; amount: number; expires_at: string | null; reason: string };
      new_effective_quota: number;
    }>(`/api/admin/tenants/${tenantId}/quota-grants`, payload),
  revokeQuotaGrant: (tenantId: string, grantId: number, reason: string) =>
    api.del<{ ok: boolean }>(`/api/admin/tenants/${tenantId}/quota-grants/${grantId}`, { reason }),
  listQuotaGrants: (tenantId: string, includeExpired = false) =>
    api.get<{
      grants: Array<{
        id: number; kind: string; amount: number; used_amount: number;
        expires_at: string | null; reason: string;
        granted_by: number; created_at: string;
      }>;
    }>(`/api/admin/tenants/${tenantId}/quota-grants${includeExpired ? '?include=all' : ''}`),

  // Feature flags (Frente 1.10)
  listGlobalFlags: () =>
    api.get<{
      flags: Array<{
        key: string; description: string | null;
        default_value: boolean; rollout_pct: number;
        created_at: string;
      }>;
    }>('/api/admin/feature-flags'),
  upsertGlobalFlag: (payload: { key: string; description?: string; default_value: boolean; rollout_pct: number }) =>
    api.post<{ ok: boolean; action: 'created' | 'updated'; flag: { key: string } }>('/api/admin/feature-flags', payload),
  listTenantFlags: (tenantId: string) =>
    api.get<{
      flags: Array<{
        key: string; description: string | null;
        value: boolean; source: 'tenant_override' | 'rollout' | 'default';
        default_value: boolean; rollout_pct: number;
        tenant_override: { enabled: boolean; set_at: string } | null;
      }>;
    }>(`/api/admin/tenants/${tenantId}/feature-flags`),
  setTenantFlag: (tenantId: string, key: string, enabled: boolean) =>
    api.put<{ ok: boolean }>(`/api/admin/tenants/${tenantId}/feature-flags/${key}`, { enabled }),
  removeTenantFlag: (tenantId: string, key: string) =>
    api.del<{ ok: boolean }>(`/api/admin/tenants/${tenantId}/feature-flags/${key}`),

  // Audit (Frente 1.12)
  listAudit: (params: { event_type?: string; actor_user_id?: number; tenant_id?: string; since?: string; until?: string; search?: string; cursor?: number; limit?: number } = {}) => {
    const q = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') q.set(k, String(v));
    });
    const qs = q.toString();
    return api.get<{
      events: Array<{
        id: number; timestamp: string; tenant_id: string | null;
        actor_user_id: number | null; impersonator_user_id: number | null;
        impersonation_id: number | null; event_type: string;
        target_type: string | null; target_id: string | null;
        payload: Record<string, unknown>; ip_address: string | null;
      }>;
      total: number; cursor_next: number | null;
    }>(`/api/admin/audit${qs ? '?' + qs : ''}`);
  },
  listTenantAudit: (tenantId: string, params: { event_type?: string; cursor?: number; limit?: number } = {}) => {
    const q = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') q.set(k, String(v));
    });
    const qs = q.toString();
    return api.get<{
      events: Array<{
        id: number; timestamp: string; tenant_id: string | null;
        actor_user_id: number | null; impersonator_user_id: number | null;
        impersonation_id: number | null; event_type: string;
        target_type: string | null; target_id: string | null;
        payload: Record<string, unknown>; ip_address: string | null;
      }>;
      total: number; cursor_next: number | null;
    }>(`/api/admin/tenants/${tenantId}/audit${qs ? '?' + qs : ''}`);
  },
};
