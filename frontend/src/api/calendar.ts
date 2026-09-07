import { api } from './client';

export type SpiritualTradition = 'crista' | 'afro' | 'paga' | 'astronomica' | 'secular';

export interface SpiritualEvent {
  id: number | null;
  date: string;
  tradition: SpiritualTradition;
  name: string;
  description: string | null;
  is_custom?: boolean;
  days_from_today?: number;
  lunar?: { phase_name: string; illumination_pct: number; special_label?: string | null };
}

export interface CalendarRangeResponse {
  from: string;
  to: string;
  events: SpiritualEvent[];
  total: number;
}

export interface TodayResponse {
  today: string;
  horizon: string;
  events: SpiritualEvent[];
}

export interface SuggestionResponse {
  ok: boolean;
  cached: boolean;
  suggestion: { messages: string[]; source: string };
}

export interface CreateCustomDatePayload {
  name: string;
  tradition: SpiritualTradition;
  month?: number;
  day?: number;
  fixed_date?: string;
  description?: string;
}

export const calendarApi = {
  range: (params: {
    from?: string;
    to?: string;
    traditions?: string;
    include_lunar?: boolean;
  } = {}) => {
    const q = new URLSearchParams();
    if (params.from) q.set('from', params.from);
    if (params.to) q.set('to', params.to);
    if (params.traditions) q.set('traditions', params.traditions);
    if (params.include_lunar === false) q.set('include_lunar', '0');
    const qs = q.toString();
    return api.get<CalendarRangeResponse>(`/saas/calendar${qs ? '?' + qs : ''}`);
  },

  today: () => api.get<TodayResponse>('/saas/calendar/today'),

  createCustom: (payload: CreateCustomDatePayload) =>
    api.post<{ ok: boolean; date: { id: number } }>('/saas/calendar/dates', payload),

  removeCustom: (id: number) =>
    api.del<{ ok: boolean }>(`/saas/calendar/dates/${id}`),

  suggestMessage: (id: number) =>
    api.post<SuggestionResponse>(`/saas/calendar/${id}/suggest-message`, {}),
};
