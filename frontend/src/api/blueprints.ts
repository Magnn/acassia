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

interface CreateBlueprintInput {
  title: string;
  integration: string;
  event: string;
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
  delete: async (id: number): Promise<{ ok: boolean }> => {
    return api.del<{ ok: boolean }>(`/api/flows/blueprints/${id}`);
  },

  // ── Validação / compilação no servidor ──────────────────────────────
  validate: (doc: Record<string, unknown>) =>
    api.post<ValidationReport>('/api/flows/lint', doc),

  // ── Publicação ──────────────────────────────────────────────────────
  publish: (blueprintId: number) =>
    api.post<{ ok: boolean; published_blueprint_id: number }>(
      '/api/flows/publish',
      { blueprint_id: blueprintId },
    ),
  unpublish: (blueprintId: number) =>
    api.delete<{ ok: boolean; published_blueprint_id: null }>(
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
  create: async ({ title, integration, event }: CreateBlueprintInput): Promise<BlueprintDetail> => {
    const triggerId = 'trigger-start';
    const endId = 'flow-end';
    const body = {
      format: 'meumisterio-flow',
      version: 1,
      title,
      graph: {
        nodes: [
          {
            id: triggerId,
            type: 'trigger',
            label: integration === 'whatsapp' ? 'WhatsApp' : integration,
            x: 80,
            y: 160,
            config: { integration, event, keyword: '' },
          },
          {
            id: endId,
            type: 'end',
            label: 'Fim',
            x: 460,
            y: 160,
            config: {},
          },
        ],
        edges: [{ id: 'edge-start-end', from: triggerId, to: endId }],
      },
    };
    const data = await api.post<{ ok: boolean; blueprint: BlueprintDetail }>(
      '/api/flows/blueprints/import',
      { title, body },
    );
    return data.blueprint;
  },

  // ── A/B Analytics ────────────────────────────────────────────────────
  abAnalytics: (blueprintId: number) =>
    api.get<ABAnalyticsResponse>(`/saas/ab/${blueprintId}/analytics`),
};

export interface ABVariantStats {
  impressions: number;
  conversions: number;
  rate: number;
  revenue: number;
}

export interface ABNodeAnalytics {
  node_id: string;
  variants: Record<string, ABVariantStats>;
  winner: string | null;
  confidence: string;
  total_impressions: number;
  total_revenue: number;
}

export interface ABAnalyticsResponse {
  blueprint_id: number;
  nodes: Record<string, ABNodeAnalytics>;
}
