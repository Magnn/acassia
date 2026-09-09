// Wrapper fino sobre fetch — credentials: 'include' carrega o cookie do flask-login
// para piggyback de auth, mesma origem em produção (servido pelo Flask em /builder).
export class ApiError extends Error {
  status: number;
  body: unknown;
  constructor(status: number, body: unknown, message: string) {
    super(message);
    this.status = status;
    this.body = body;
  }

  /**
   * True se erro é "quota exceeded" (HTTP 402 com error="quota_exceeded").
   * Frontend pode fallback pra mostrar modal de upgrade.
   */
  get isQuotaExceeded(): boolean {
    if (this.status !== 402) return false;
    const b = this.body as { error?: string } | null;
    return b?.error === 'quota_exceeded';
  }

  get quotaInfo(): { kind: string; current: number; limit: number; message: string } | null {
    if (!this.isQuotaExceeded) return null;
    const b = this.body as { kind?: string; current?: number; limit?: number; message?: string };
    return {
      kind: b.kind || 'unknown',
      current: b.current || 0,
      limit: b.limit || 0,
      message: b.message || 'Limite do plano atingido',
    };
  }
}

let authRedirectStarted = false;

export function loginUrl(): string {
  if (typeof window === 'undefined') return '/saas/login';
  const current = window.location.pathname + window.location.search + window.location.hash;
  return `/saas/login?next=${encodeURIComponent(current)}`;
}

export function redirectToLogin(): void {
  if (typeof window === 'undefined' || authRedirectStarted) return;
  const path = window.location.pathname;
  if (path.startsWith('/saas/login') || path.startsWith('/saas/signup')) return;
  authRedirectStarted = true;
  window.location.replace(loginUrl());
}

export function isAuthError(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401;
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = { Accept: 'application/json' };
  if (body !== undefined) headers['Content-Type'] = 'application/json';

  const b2cToken = typeof window !== 'undefined' ? localStorage.getItem('b2c_access_token') : null;
  if (b2cToken && (path.startsWith('/api/b2c') || path.startsWith('/b2c'))) {
    headers['Authorization'] = `Bearer ${b2cToken}`;
  }

  const res = await fetch(path, {
    method,
    credentials: 'include',
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  const text = await res.text();
  const data = text ? safeJson(text) : null;
  if (!res.ok) {
    const serverMessage =
      data && typeof data === 'object'
        ? String((data as { error?: unknown; message?: unknown }).error
          || (data as { message?: unknown }).message
          || '')
        : '';

    // Sessão expirada ou não autenticado no SaaS: redireciona para login limpo
    if (res.status === 401 && typeof window !== 'undefined') {
      const isB2C = path.startsWith('/api/b2c') || path.startsWith('/b2c') || window.location.pathname.startsWith('/portal');
      const isAlreadyOnAuth = window.location.pathname.includes('/login') || window.location.pathname.includes('/signup');
      if (!isB2C && !isAlreadyOnAuth) redirectToLogin();
    }

    throw new ApiError(
      res.status,
      data,
      serverMessage || `${method} ${path} → ${res.status}`,
    );
  }
  return data as T;
}

function safeJson(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

export const api = {
  get: <T>(path: string) => request<T>('GET', path),
  post: <T>(path: string, body?: unknown) => request<T>('POST', path, body),
  put: <T>(path: string, body?: unknown) => request<T>('PUT', path, body),
  patch: <T>(path: string, body?: unknown) => request<T>('PATCH', path, body),
  del: <T>(path: string, body?: unknown) => request<T>('DELETE', path, body),
  delete: <T>(path: string, body?: unknown) => request<T>('DELETE', path, body),
  upload: async <T>(path: string, formData: FormData): Promise<T> => {
    const res = await fetch(path, {
      method: 'POST',
      credentials: 'include',
      headers: { Accept: 'application/json' },
      body: formData,
    });
    const text = await res.text();
    const data = text ? safeJson(text) : null;
    if (!res.ok) {
      const serverMessage =
        data && typeof data === 'object'
          ? String(
              (data as { error?: unknown; message?: unknown }).error ||
                (data as { message?: unknown }).message ||
                '',
            )
          : '';

      if (res.status === 401 && typeof window !== 'undefined') {
        const isB2C = path.startsWith('/api/b2c') || path.startsWith('/b2c') || window.location.pathname.startsWith('/portal');
        const isAlreadyOnAuth = window.location.pathname.includes('/login') || window.location.pathname.includes('/signup');
        if (!isB2C && !isAlreadyOnAuth) redirectToLogin();
      }

      throw new ApiError(
        res.status,
        data,
        serverMessage || `POST ${path} → ${res.status}`,
      );
    }
    return data as T;
  },
};
