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

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = { Accept: 'application/json' };
  if (body !== undefined) headers['Content-Type'] = 'application/json';
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
};
