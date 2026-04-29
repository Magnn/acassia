import { api } from './client';

export interface FlowTemplate {
  id: string;
  name: string;
  description: string | null;
  category: string | null;
  ticket_brl_avg: number;
  preview_image_url: string | null;
  usage_count: number;
  is_official: boolean;
  node_count: number;
  price_brl_cents: number;
}

export interface FlowTemplateDetail extends FlowTemplate {
  blueprint_json: Record<string, unknown>;
  agent_json: Record<string, unknown> | null;
}

export const templatesApi = {
  list: (category?: string) =>
    api.get<{ templates: FlowTemplate[] }>(
      `/saas/templates${category ? `?category=${encodeURIComponent(category)}` : ''}`,
    ),
  get: (id: string) =>
    api.get<FlowTemplateDetail>(`/saas/templates/${id}`),
  apply: (id: string, custom?: { custom_title?: string; custom_slug?: string }) =>
    api.post<{
      ok: boolean;
      blueprint_id: number;
      blueprint_slug: string;
      agent_id: number | null;
      redirect: string;
    }>(`/saas/templates/${id}/apply`, custom || {}),
};
