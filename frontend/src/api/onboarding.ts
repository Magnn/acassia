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
  skip_validation?: boolean;
}

export interface WhatsAppStepResult {
  phone_number_id: string;
  verify_token: string;
  webhook_url: string;
  subscribed: boolean;
  subscribe_error: string | null;
  display_phone_number: string | null;
}

interface StepResponse {
  ok: boolean;
  next_step: 'persona' | 'oferta' | 'template' | 'whatsapp' | 'done';
  current_step?: string;
  error?: string;
  binding?: WhatsAppStepResult;
  instructions?: string[];
}

export const onboardingApi = {
  // Backend index() retorna JSON quando Accept inclui application/json — o
  // client.ts já manda isso por default; resposta tem { current_step, done? }.
  getStatus: () =>
    api.get<{ current_step: StepResponse['next_step']; done?: boolean }>(
      '/saas/onboarding/',
    ),
  savePersona: (data: PersonaDraft) =>
    api.post<StepResponse>('/saas/onboarding/persona', data),
  saveOferta: (data: OfertaDraft) =>
    api.post<StepResponse>('/saas/onboarding/oferta', data),
  saveTemplate: (data: TemplateDraft) =>
    api.post<StepResponse>('/saas/onboarding/template', data),
  saveWhatsApp: (data: WhatsAppDraft) =>
    api.post<StepResponse>('/saas/onboarding/whatsapp', data),
};
