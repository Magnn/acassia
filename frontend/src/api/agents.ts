import { api } from './client';

export interface AgentDraft {
  personalidade?: string;
  instrucoes?: string;
  base_conhecimento?: string;
  faqs?: { q: string; a: string }[];
  arquivos?: { nome: string; url: string }[];
  [k: string]: unknown;
}

export interface AgentSummary {
  id: number;
  name: string;
  avatar: string;
  draft?: AgentDraft;
  draft_version?: number;
  versions?: { id: number; version_number: number; note?: string | null; created_at: string }[];
  published_version_id?: number | null;
  criado_em?: string;
  atualizado_em?: string;
}

export interface AgentVersion {
  id: number;
  version_number: number;
  body?: AgentDraft;
  note: string | null;
  created_at: string;
}

export const agentsApi = {
  list: async (): Promise<AgentSummary[]> => {
    const data = await api.get<{ ok: boolean; agents: AgentSummary[] }>(
      '/api/studio/agents',
    );
    return data.agents;
  },
  get: async (id: number): Promise<AgentSummary> => {
    const data = await api.get<{ ok: boolean; agent: AgentSummary }>(
      `/api/studio/agents/${id}`,
    );
    return data.agent;
  },
  create: (input: { name: string; avatar?: string }) =>
    api.post<{ ok: boolean; agent: AgentSummary }>(
      '/api/studio/agents',
      input,
    ),
  update: (id: number, input: Partial<{ name: string; avatar: string; draft: AgentDraft }>) =>
    api.patch<{ ok: boolean; agent: AgentSummary }>(
      `/api/studio/agents/${id}`,
      input,
    ),
  remove: (id: number) =>
    api.del<{ ok: boolean }>(`/api/studio/agents/${id}`),
  snapshot: (id: number, note?: string) =>
    api.post<{ ok: boolean; version: AgentVersion }>(
      `/api/studio/agents/${id}/versions`,
      { note: note || null },
    ),
  publish: (agentId: number, versionId: number) =>
    api.post<{ ok: boolean; published_version_id: number }>(
      `/api/studio/agents/${agentId}/publish`,
      { version_id: versionId },
    ),
  publishStatus: () =>
    api.get<{
      ok: boolean;
      published: { agent_id: number; version_id: number; version_number: number } | null;
    }>('/api/studio/publish/status'),
};
