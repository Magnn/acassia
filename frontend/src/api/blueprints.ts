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

interface ListResponse {
  ok: boolean;
  blueprints: BlueprintSummary[];
}

interface DetailResponse {
  ok: boolean;
  blueprint: BlueprintDetail;
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
};
