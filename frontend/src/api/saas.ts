import { api } from './client';

/* ── Scheduling ─────────────────────────────────────── */
export interface Slot {
  id: number;
  slot_time: string;
  slot_date: string | null;
  duration_minutes: number;
  is_booked: boolean;
  is_blocked: boolean;
  lead_id: number | null;
}

export interface Appointment {
  id: number;
  status: 'pending' | 'confirmed' | 'completed' | 'cancelled' | 'no_show';
  client_name: string;
  client_phone: string;
  scheduled_at: string;
  duration_minutes: number;
  modality: string;
  service_id: number | null;
  notes_before: string | null;
}

export const schedulingApi = {
  slots: (p?: { from?: string; to?: string }) => {
    const q = new URLSearchParams();
    if (p?.from) q.set('from', p.from);
    if (p?.to) q.set('to', p.to);
    return api.get<{ slots: Slot[] }>(`/saas/scheduling/slots?${q}`);
  },
  createSlot: (b: { date: string; start_time: string; end_time: string; duration_minutes: number }) =>
    api.post<{ ok: boolean; ids: number[] }>('/saas/scheduling/slots', b),
  bulkSlots: (b: { dates: string[]; start_time: string; end_time: string; duration_minutes: number }) =>
    api.post<{ ok: boolean; total: number }>('/saas/scheduling/slots/bulk', b),
  appointments: (p?: { status?: string }) => {
    const q = p?.status ? `?status=${p.status}` : '';
    return api.get<{ appointments: Appointment[] }>(`/saas/scheduling/appointments${q}`);
  },
  today: () => api.get<{ appointments: Appointment[] }>('/saas/scheduling/today'),
  updateAppointment: (id: number, b: { status: string; notes_after?: string }) =>
    api.put<{ ok: boolean }>(`/saas/scheduling/appointments/${id}`, b),
  availability: () => api.get<{ availability: Record<string, Slot[]> }>('/saas/scheduling/availability'),
};

/* ── Profile ────────────────────────────────────────── */
export interface Profile {
  id?: number;
  slug: string;
  display_name: string;
  headline: string | null;
  bio: string | null;
  avatar_url: string | null;
  specialties: string[];
  city: string | null;
  state: string | null;
  instagram: string | null;
  theme_color: string;
  show_services: boolean;
  show_testimonials: boolean;
  show_calendar: boolean;
  accept_online: boolean;
  is_published: boolean;
  total_views: number;
  exists: boolean;
  url: string;
}

export interface Testimonial {
  id: number;
  client_name: string;
  text: string;
  rating: number;
  service_type: string | null;
  is_approved: boolean;
  created_at: string;
}

export const profileApi = {
  get: () => api.get<Profile>('/saas/profile/'),
  upsert: (b: Partial<Profile>) => api.post<{ ok: boolean; slug: string; url: string }>('/saas/profile/', b),
  publish: () => api.post<{ ok: boolean; url: string }>('/saas/profile/publish'),
  stats: () => api.get<{ total_views: number; total_bookings: number; is_published: boolean; slug: string }>('/saas/profile/stats'),
  testimonials: () => api.get<{ testimonials: Testimonial[] }>('/saas/profile/testimonials'),
  addTestimonial: (b: { client_name: string; text: string; rating?: number; service_type?: string }) =>
    api.post<{ ok: boolean; id: number }>('/saas/profile/testimonials', b),
  deleteTestimonial: (id: number) => api.del<{ ok: boolean }>(`/saas/profile/testimonials/${id}`),
};

/* ── Events ─────────────────────────────────────────── */
export interface Event {
  id: number;
  title: string;
  description: string | null;
  event_type: string;
  start_date: string;
  end_date: string;
  location: string | null;
  max_attendees: number | null;
  price_cents: number;
  early_bird_price_cents: number | null;
  status: string;
  total_registered: number;
}

export const eventsApi = {
  list: () => api.get<{ events: Event[] }>('/saas/events/'),
  create: (b: Partial<Event>) => api.post<{ ok: boolean; id: number }>('/saas/events/', b),
  get: (id: number) => api.get<Event>(`/saas/events/${id}`),
  update: (id: number, b: Partial<Event>) => api.put<{ ok: boolean }>(`/saas/events/${id}`, b),
  registrations: (id: number) => api.get<{ registrations: Array<{ id: number; name: string; phone: string; status: string; registered_at: string }> }>(`/saas/events/${id}/registrations`),
};

/* ── Content (Infoprodutos) ─────────────────────────── */
export interface ContentAsset {
  id: number;
  title: string;
  description: string | null;
  asset_type: string;
  price_cents: number;
  file_url: string | null;
  cover_image_url: string | null;
  is_published: boolean;
  total_sales: number;
  created_at: string;
}

export const contentApi = {
  list: () => api.get<{ assets: ContentAsset[] }>('/saas/content/'),
  create: (b: Partial<ContentAsset>) => api.post<{ ok: boolean; id: number }>('/saas/content/', b),
  get: (id: number) => api.get<ContentAsset>(`/saas/content/${id}`),
  update: (id: number, b: Partial<ContentAsset>) => api.put<{ ok: boolean }>(`/saas/content/${id}`, b),
};

/* ── Broadcast ──────────────────────────────────────── */
export interface Campaign {
  id: number;
  name: string;
  message_template: string;
  segment_filters: Record<string, unknown>;
  status: string;
  total_recipients: number;
  total_sent: number;
  total_delivered: number;
  total_failed: number;
  created_at: string;
  sent_at: string | null;
  scheduled_at?: string | null;
}

export const broadcastApi = {
  campaigns: () => api.get<{ campaigns: Campaign[] }>('/saas/broadcast/'),
  create: (b: { name: string; message_template: string; segment_filters?: Record<string, unknown>; scheduled_at?: string; status?: string }) =>
    api.post<{ ok: boolean; id: number }>('/saas/broadcast/', b),
  preview: (id: number) => api.post<{ preview: Array<{ lead_id: number; nome: string }> }>(`/saas/broadcast/${id}/preview`),
  send: (id: number) => api.post<{ ok: boolean; total_queued: number }>(`/saas/broadcast/${id}/send`),
};

/* ── Subscriptions (Pacotes) ────────────────────────── */
export interface Subscription {
  id: number;
  lead_id: number;
  lead_name: string | null;
  package_name: string;
  sessions_included: number;
  sessions_used: number;
  price_cents: number;
  period_days: number;
  status: string;
  current_period_start: string;
  current_period_end: string;
}

export const subscriptionsApi = {
  list: () => api.get<{ subscriptions: Subscription[] }>('/saas/subscriptions/'),
  create: (b: { lead_id?: number; package_name: string; sessions_included: number; price_cents: number; period_days: number }) =>
    api.post<{ ok: boolean; id: number }>('/saas/subscriptions/', b),
  get: (id: number) => api.get<Subscription>(`/saas/subscriptions/${id}`),
  pause: (id: number) => api.post<{ ok: boolean }>(`/saas/subscriptions/${id}/pause`),
  resume: (id: number) => api.post<{ ok: boolean }>(`/saas/subscriptions/${id}/resume`),
  renew: (id: number) => api.post<{ ok: boolean }>(`/saas/subscriptions/${id}/renew`),
};

/* ── Journal ────────────────────────────────────────── */
export interface JournalEntry {
  id: number;
  entry_type: string;
  title: string | null;
  content: string;
  mood: string | null;
  mood_emoji: string;
  energy_level: number | null;
  tags: string[];
  ai_insight: string | null;
  streak_day: number;
  entry_date: string;
  created_at: string;
}

export const journalApi = {
  list: (p?: { type?: string; limit?: number; page?: number }) => {
    const q = new URLSearchParams();
    if (p?.type) q.set('type', p.type);
    if (p?.limit) q.set('limit', String(p.limit));
    if (p?.page) q.set('page', String(p.page));
    return api.get<{ entries: JournalEntry[]; total: number; page: number; pages: number }>(`/saas/journal/?${q}`);
  },
  create: (b: { content: string; entry_type?: string; title?: string; mood?: string; energy_level?: number; tags?: string[]; generate_insight?: boolean }) =>
    api.post<{ ok: boolean; id: number; streak: number; badges_earned?: Array<{ name: string; icon: string; xp: number }> }>('/saas/journal/', b),
  stats: () => api.get<{ total_entries: number; current_streak: number; best_streak: number; mood_distribution: Record<string, number>; avg_energy_7d: number | null; badges: Array<{ name: string; icon: string; earned_at: string }> }>('/saas/journal/stats'),
  prompt: (b: { entry_type?: string; mood?: string }) => api.post<{ prompt: string }>('/saas/journal/prompt', b),
  moods: (days?: number) => api.get<{ moods: Array<{ date: string; mood: string; emoji: string; energy: number | null }> }>(`/saas/journal/moods?days=${days || 30}`),
  del: (id: number) => api.del<{ ok: boolean }>(`/saas/journal/${id}`),
};

/* ── Trails ─────────────────────────────────────────── */
export interface Trail {
  id: number;
  title: string;
  description: string | null;
  category: string;
  difficulty: string;
  duration_days: number;
  xp_reward: number;
  badge_name: string | null;
  badge_icon: string | null;
  is_published: boolean;
  total_enrollments: number;
  total_completions: number;
}

export interface TrailStep {
  id: number;
  day_number: number;
  title: string;
  content: string | null;
  content_type: string;
  action_type: string | null;
  xp_reward: number;
  is_completed?: boolean;
  is_locked?: boolean;
}

export const trailsApi = {
  list: () => api.get<{ trails: Trail[] }>('/saas/trails/'),
  create: (b: Partial<Trail>) => api.post<{ ok: boolean; id: number }>('/saas/trails/', b),
  get: (id: number) => api.get<Trail & { steps: TrailStep[] }>(`/saas/trails/${id}`),
  update: (id: number, b: Partial<Trail>) => api.put<{ ok: boolean }>(`/saas/trails/${id}`, b),
  publish: (id: number) => api.post<{ ok: boolean }>(`/saas/trails/${id}/publish`),
  addStep: (id: number, b: Partial<TrailStep>) => api.post<{ ok: boolean; id: number }>(`/saas/trails/${id}/steps`, b),
  catalog: () => api.get<{ trails: Trail[] }>('/saas/trails/catalog'),
  badges: () => api.get<{ badges: Array<{ id: number; name: string; icon: string; type: string; description: string; xp: number; earned_at: string }>; total_xp: number }>('/saas/trails/badges'),
};
