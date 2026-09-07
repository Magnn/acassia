import { api } from './client';

export interface FlowRun {
  id: number;
  blueprint_id: number;
  lead_id: number | null;
  status: string;
  meta: Record<string, unknown>;
  started_at: string;
  finished_at: string | null;
}

export interface FlowRunEvent {
  id: number;
  run_id: number;
  node_id: string | null;
  type: string;
  payload: Record<string, unknown>;
  ts: string;
}

export const runsApi = {
  list: async (params: { blueprintId?: number; limit?: number } = {}): Promise<FlowRun[]> => {
    const q = new URLSearchParams();
    if (params.blueprintId) q.set('blueprint_id', String(params.blueprintId));
    if (params.limit) q.set('limit', String(params.limit));
    const qs = q.toString();
    const data = await api.get<{ ok: boolean; runs: FlowRun[] }>(
      `/api/flows/runs${qs ? `?${qs}` : ''}`,
    );
    return data.runs;
  },
  get: async (id: number): Promise<FlowRun> => {
    const data = await api.get<{ ok: boolean; run: FlowRun }>(
      `/api/flows/runs/${id}`,
    );
    return data.run;
  },
  events: async (id: number): Promise<FlowRunEvent[]> => {
    const data = await api.get<{ ok: boolean; events: FlowRunEvent[] }>(
      `/api/flows/runs/${id}/events`,
    );
    return data.events;
  },
};
