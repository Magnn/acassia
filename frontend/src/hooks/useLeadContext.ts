import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';

export interface LeadContext {
  lead: {
    id: number;
    telefone: string;
    nome: string | null;
    email: string | null;
    signo: string | null;
    idade: number | null;
    cidade: string | null;
    tags: string[];
    custom_fields: Record<string, unknown>;
    criado_em: string | null;
  };
  score: {
    value: number;
    band: 'hot' | 'warm' | 'cold';
    components: Record<string, number>;
    updated_at: string | null;
  };
  journey: {
    node_atual: string | null;
    node_historico: string[];
    depth: number;
    time_in_node_s: number | null;
    last_msg_at: string | null;
    convertido: boolean;
    bot_pausado: boolean;
    opt_out: boolean;
  };
  sentiment: {
    recent: string[];
    positive_count: number;
    negative_count: number;
    trend: 'positive' | 'negative' | 'neutral';
  };
  commercial: {
    payments_count: number;
    payments: Array<{
      id: number;
      provider: string;
      event_type: string;
      processed_at: string | null;
    }>;
  };
  tarot_readings_count: number;
}

export function useLeadContext(leadId: number | null) {
  return useQuery({
    queryKey: ['lead-context', leadId],
    queryFn: () => api.get<LeadContext>(`/saas/inbox/${leadId}/context`),
    enabled: leadId !== null,
    staleTime: 30_000,
  });
}
