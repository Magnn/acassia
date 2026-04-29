import { api } from './client';

export interface PersonaDraft {
  name: string;
  tone: string;
  backstory: string;
  restrictions: string[];
}

export interface OfertaDraft {
  nome: string;
  preco: string;
  descricao: string;
  gateway: string;
}

export interface TemplateDraft {
  template: string;
}

export interface WhatsAppDraft {
  phone_number_id: string;
  waba_id: string;
  access_token: string;
}

interface StepResponse {
  ok: boolean;
  next_step: 'persona' | 'oferta' | 'template' | 'whatsapp' | 'done';
  current_step?: string;
  error?: string;
}

export const onboardingApi = {
  getStatus: () =>
    api.get<{ current_step: StepResponse['next_step'] }>(
      '/saas/onboarding/status/data',
    ),
  savePersona: (data: PersonaDraft) =>
    api.post<StepResponse>('/saas/onboarding/persona/data', data),
  saveOferta: (data: OfertaDraft) =>
    api.post<StepResponse>('/saas/onboarding/oferta/data', data),
  saveTemplate: (data: TemplateDraft) =>
    api.post<StepResponse>('/saas/onboarding/template/data', data),
  saveWhatsApp: (data: WhatsAppDraft) =>
    api.post<StepResponse>('/saas/onboarding/whatsapp/data', data),
};
