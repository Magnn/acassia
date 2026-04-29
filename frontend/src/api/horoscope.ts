import { api } from './client';

export interface HoroscopeConfig {
  id: number;
  enabled: boolean;
  send_hour_local: number;
  timezone: string;
  source: 'gemini' | 'manual';
  segment_filter: 'all' | 'hot' | 'warm' | 'hot_warm';
  custom_prefix: string | null;
  last_run_date: string | null;
  total_sent: number;
}

export interface HoroscopeStats {
  candidates_with_sign: number;
  opted_in: number;
}

export interface SignText {
  signo: string;
  text: string;
}

export interface DeliveryRow {
  id: number;
  lead_id: number;
  date: string;
  signo: string;
  status: string;
  error_message: string | null;
  sent_at: string;
}

export interface DeliveriesResponse {
  days: number;
  summary: Record<string, number>;
  deliveries: DeliveryRow[];
}

export interface FanoutStats {
  sent: number;
  skipped: number;
  failed: number;
  opted_out: number;
  by_sign: Record<string, number>;
  reason?: string;
}

export const horoscopeApi = {
  getConfig: () =>
    api.get<{ config: HoroscopeConfig; stats: HoroscopeStats }>('/saas/horoscope/config'),

  patchConfig: (patch: Partial<HoroscopeConfig>) =>
    api.patch<{ ok: boolean; config: HoroscopeConfig }>('/saas/horoscope/config', patch),

  today: () =>
    api.get<{ date: string; signs: SignText[] }>('/saas/horoscope/today'),

  preview: (signo: string, force = false) =>
    api.post<{ signo: string; text: string; source: string; generated_by: string | null; date: string }>(
      `/saas/horoscope/preview/${signo}`,
      { force },
    ),

  runNow: (dryRun = false) =>
    api.post<{ ok: boolean; dry_run: boolean; stats: FanoutStats }>(
      '/saas/horoscope/run-now',
      { dry_run: dryRun },
    ),

  deliveries: (days = 7) =>
    api.get<DeliveriesResponse>(`/saas/horoscope/deliveries?days=${days}`),

  backfillSigns: () =>
    api.post<{ ok: boolean; updated: number }>('/saas/horoscope/backfill-signs', {}),
};
