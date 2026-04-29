export interface LeadPreview {
  id: number;
  telefone: string;
  nome: string;
  node_atual: string;
  convertido: boolean;
  bot_pausado: boolean;
  opt_out: boolean;
  ultima_msg: string;
  ultima_em: string | null;
}

export interface LeadMessage {
  id: number;
  texto: string;
  origem: string;
  timestamp: string | null;
  media_url?: string;
  media_type?: string;
}

export interface LeadDetail {
  id: number;
  telefone: string;
  nome: string;
  bot_pausado: boolean;
  node_atual: string;
}

export interface ConversationData {
  lead: LeadDetail;
  messages: LeadMessage[];
}

export const inboxApi = {
  getLeads: async (filtro = 'todos'): Promise<{ items: LeadPreview[]; filtro: string }> => {
    const res = await fetch(`/saas/inbox/data?filtro=${filtro}`);
    if (!res.ok) throw new Error('Failed to fetch leads');
    return res.json();
  },

  getConversation: async (leadId: number): Promise<ConversationData> => {
    const res = await fetch(`/saas/inbox/${leadId}/data`);
    if (!res.ok) throw new Error('Failed to fetch conversation');
    return res.json();
  },

  toggleTakeover: async (leadId: number): Promise<{ status: string; bot_pausado: boolean }> => {
    const res = await fetch(`/saas/inbox/${leadId}/takeover/data`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error('Failed to toggle takeover');
    return res.json();
  },
};
