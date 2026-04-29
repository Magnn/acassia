import { api } from './client';

export interface BlueprintSummary {
  id: number;
  slug: string;
  title: string;
  updated_at: string;
  created_at: string;
}

export interface BlueprintDetail extends BlueprintSummary {
  body: Record<string, unknown>;
}

export interface BlueprintVersion {
  id: number;
  version_number: number;
  note: string | null;
  created_at: string;
}

export interface ValidationIssue {
  code?: string;
  level?: string;
  message?: string;
  node?: string;
  edge?: string;
}

export interface ValidationReport {
  ok: boolean;
  errors?: ValidationIssue[];
  warnings?: ValidationIssue[];
  normalized?: Record<string, unknown>;
  error?: string;
}

export interface PublishStatus {
  blueprint_id: number;
  slug: string;
  title: string;
}

interface ListResponse {
  ok: boolean;
  blueprints: BlueprintSummary[];
}

interface DetailResponse {
  ok: boolean;
  blueprint: BlueprintDetail;
}

interface UpdateInput {
  title?: string;
  slug?: string;
  body?: Record<string, unknown>;
}

export const blueprintsApi = {
  list: async (): Promise<BlueprintSummary[]> => {
    const data = await api.get<ListResponse>('/api/flows/blueprints');
    return data.blueprints;
  },
  get: async (id: number): Promise<BlueprintDetail> => {
    const data = await api.get<DetailResponse>(`/api/flows/blueprints/${id}`);
    return data.blueprint;
  },
  update: async (id: number, input: UpdateInput): Promise<BlueprintSummary> => {
    const data = await api.patch<{ ok: boolean; blueprint: BlueprintSummary }>(
      `/api/flows/blueprints/${id}`,
      input,
    );
    return data.blueprint;
  },

  // ── Validação / compilação no servidor ──────────────────────────────
  validate: (doc: Record<string, unknown>) =>
    api.post<ValidationReport>('/api/flows/validate', doc),

  // ── Publicação ──────────────────────────────────────────────────────
  publish: (blueprintId: number) =>
    api.post<{ ok: boolean; published_blueprint_id: number }>(
      '/api/flows/publish',
      { blueprint_id: blueprintId },
    ),
  publishStatus: () =>
    api.get<{ ok: boolean; published: PublishStatus | null }>(
      '/api/flows/publish/status',
    ),

  // ── Versões ─────────────────────────────────────────────────────────
  listVersions: async (id: number): Promise<BlueprintVersion[]> => {
    const data = await api.get<{ ok: boolean; versions: BlueprintVersion[] }>(
      `/api/flows/blueprints/${id}/versions`,
    );
    return data.versions;
  },
  createVersion: (id: number, note?: string) =>
    api.post<{ ok: boolean; version: BlueprintVersion }>(
      `/api/flows/blueprints/${id}/versions`,
      { note: note || null },
    ),
  restoreVersion: (id: number, versionId: number) =>
    api.post<{ ok: boolean }>(
      `/api/flows/blueprints/${id}/versions/${versionId}/restore`,
    ),

  // ── Export / Import ─────────────────────────────────────────────────
  exportOne: (id: number) =>
    api.get<Record<string, unknown>>(`/api/flows/blueprints/${id}/export`),
  importOne: (payload: { title: string; slug?: string; body: Record<string, unknown> }) =>
    api.post<{ ok: boolean; blueprint: BlueprintDetail }>(
      '/api/flows/blueprints/import',
      payload,
    ),
  create: async (title: string): Promise<BlueprintDetail> => {
    const data = await api.post<{ ok: boolean; blueprint: BlueprintDetail }>(
      '/api/flows/blueprints/import',
      { title, body: { format: 'acassia-flow', version: 1, graph: { nodes: [], edges: [] } } },
    );
    return data.blueprint;
  },
};
