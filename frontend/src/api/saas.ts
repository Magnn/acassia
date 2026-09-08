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
  title?: string;
  name?: string;
  message_text?: string;
  message_template?: string;
  message_media_url?: string | null;
  message_media_type?: string | null;
  segment_filters: Record<string, unknown>;
  status: 'draft' | 'scheduled' | 'sending' | 'completed' | 'cancelled' | 'failed' | string;
  total_recipients: number;
  total_sent?: number;
  sent_count?: number;
  total_delivered?: number;
  delivered_count?: number;
  total_failed?: number;
  failed_count?: number;
  reply_count?: number;
  created_at: string;
  started_at?: string | null;
  sent_at?: string | null;
  scheduled_at?: string | null;
  completed_at?: string | null;
}

export interface BroadcastRecipientItem {
  id: number;
  lead_id: number;
  lead_name: string | null;
  lead_phone: string | null;
  status: 'pending' | 'sent' | 'delivered' | 'failed' | 'replied' | string;
  sent_at: string | null;
  error_reason: string | null;
}

export const broadcastApi = {
  campaigns: () => api.get<{ campaigns: Campaign[] }>('/saas/broadcast/'),
  get: (id: number) => api.get<Campaign>(`/saas/broadcast/${id}`),
  create: (b: {
    title?: string;
    name?: string;
    message_text?: string;
    message_template?: string;
    message_media_url?: string | null;
    message_media_type?: string | null;
    segment_filters?: Record<string, unknown>;
    scheduled_at?: string | null;
    status?: string;
  }) => api.post<{ ok: boolean; id: number; status: string }>('/saas/broadcast/', b),
  update: (id: number, b: Partial<{
    title: string;
    name: string;
    message_text: string;
    message_template: string;
    message_media_url: string | null;
    segment_filters: Record<string, unknown>;
    scheduled_at: string | null;
  }>) => api.put<{ ok: boolean }>(`/saas/broadcast/${id}`, b),
  delete: (id: number) => api.delete<{ ok: boolean; action: string }>(`/saas/broadcast/${id}`),
  previewSegment: (filters: Record<string, unknown>) =>
    api.post<{
      total_matching: number;
      sample: Array<{ id: number; nome: string | null; telefone: string; signo?: string; score_band?: string; tags?: string[] }>;
    }>('/saas/broadcast/segments/preview', { filters }),
  preview: (id: number) =>
    api.post<{
      total_matching: number;
      sample: Array<{ id: number; nome: string | null; telefone: string; signo?: string; score_band?: string }>;
    }>(`/saas/broadcast/${id}/preview`),
  recipients: (id: number) =>
    api.get<{ recipients: BroadcastRecipientItem[] }>(`/saas/broadcast/${id}/recipients`),
  send: (id: number) =>
    api.post<{ ok: boolean; total_recipients: number; total_queued?: number; status: string; message: string }>(`/saas/broadcast/${id}/send`),
  duplicate: (id: number) =>
    api.post<{ ok: boolean; id: number; title: string }>(`/saas/broadcast/${id}/duplicate`),
  resendFailed: (id: number) =>
    api.post<{ ok: boolean; total_retrying: number; message: string }>(`/saas/broadcast/${id}/resend-failed`),
  pause: (id: number) =>
    api.post<{ ok: boolean; status: string; message: string }>(`/saas/broadcast/${id}/pause`),
  resume: (id: number) =>
    api.post<{ ok: boolean; status: string; message: string }>(`/saas/broadcast/${id}/resume`),
  moveToDraft: (id: number) =>
    api.post<{ ok: boolean; status: string; message: string }>(`/saas/broadcast/${id}/move-to-draft`),
  rename: (id: number, title: string) =>
    api.patch<{ ok: boolean; id: number; title: string }>(`/saas/broadcast/${id}/rename`, { title }),
  tags: () => api.get<{ tags: string[] }>('/saas/broadcast/tags'),
};

/* ── Sequences (Drip Campaigns) ────────────────────────── */
export interface SequenceStepItem {
  id: number;
  order: number;
  delay_days: number;
  delay_minutes: number;
  delay_unit: string;
  specific_date_time?: string | null;
  is_active: boolean;
  anytime: boolean;
  send_time_start?: string | null;
  send_time_end?: string | null;
  send_days?: string[];
  flow_id?: string | null;
  message_template?: string | null;
  sent_count?: number;
  delivered_count?: number;
  seen_count?: number;
  clicked_count?: number;
  failed_count?: number;
}

export interface SequenceItem {
  id: number;
  name: string;
  active: boolean;
  folder_name?: string | null;
  trigger_tag?: string | null;
  subscribers: number;
  messages: number;
  created_at?: string | null;
  updated_at?: string | null;
  steps?: SequenceStepItem[];
  stats?: {
    sent: number;
    delivered: number;
    seen: number;
    clicked: number;
    failed: number;
  };
}

export interface EnrolledContactItem {
  id: number;
  lead_id: number;
  name: string;
  phone: string;
  current_step: number;
  status: string;
  enrolled_at?: string | null;
  next_run_at?: string | null;
  completed_at?: string | null;
}

export const sequencesApi = {
  list: () => api.get<{ sequences: SequenceItem[] }>('/saas/sequences'),
  get: (id: number) => api.get<{ sequence: SequenceItem }>(`/saas/sequences/${id}`),
  create: (body: { name: string; folder_name?: string; trigger_tag?: string }) =>
    api.post<{ ok: boolean; sequence: SequenceItem }>('/saas/sequences', body),
  update: (id: number, body: { name?: string; active?: boolean; folder_name?: string; trigger_tag?: string | null }) =>
    api.put<{ ok: boolean; sequence: SequenceItem }>(`/saas/sequences/${id}`, body),
  rename: (id: number, name: string) =>
    api.patch<{ ok: boolean; id: number; name: string }>(`/saas/sequences/${id}/rename`, { name }),
  delete: (id: number) =>
    api.delete<{ ok: boolean; message: string }>(`/saas/sequences/${id}`),
  addStep: (sequenceId: number, body: Partial<SequenceStepItem>) =>
    api.post<{ ok: boolean; step: SequenceStepItem }>(`/saas/sequences/${sequenceId}/steps`, body),
  updateStep: (sequenceId: number, stepId: number, body: Partial<SequenceStepItem>) =>
    api.put<{ ok: boolean; step_id: number }>(`/saas/sequences/${sequenceId}/steps/${stepId}`, body),
  deleteStep: (sequenceId: number, stepId: number) =>
    api.delete<{ ok: boolean; message: string }>(`/saas/sequences/${sequenceId}/steps/${stepId}`),
  enroll: (sequenceId: number, lead_ids: number[]) =>
    api.post<{ ok: boolean; enrolled_count: number; message: string }>(`/saas/sequences/${sequenceId}/enroll`, { lead_ids }),
  unenroll: (sequenceId: number, lead_id: number) =>
    api.post<{ ok: boolean; message: string }>(`/saas/sequences/${sequenceId}/unenroll`, { lead_id }),
  contacts: (sequenceId: number) =>
    api.get<{ contacts: EnrolledContactItem[] }>(`/saas/sequences/${sequenceId}/contacts`),
  processDue: () =>
    api.post<{ ok: boolean; processed: number }>('/saas/sequences/process-due'),
};

/* ── Contacts Import & Sync ────────────────────────── */
export interface ContactImportItem {
  id: number;
  name: string;
  status: string;
  total_rows: number;
  processed_rows: number;
  success_rows: number;
  failed_rows: number;
  created_at?: string | null;
  completed_at?: string | null;
  error_log?: Array<{ row?: number; reason: string }>;
}

export const contactsImportApi = {
  list: () => api.get<{ imports: ContactImportItem[] }>('/saas/contacts/imports'),
  processImport: (body: {
    name: string;
    rows: Array<Record<string, any>>;
    mapping: Record<string, string>;
    assigned_tags?: string[];
    enroll_sequence_id?: number | null;
  }) =>
    api.post<{
      ok: boolean;
      import_id: number;
      total_rows: number;
      success_rows: number;
      failed_rows: number;
      message: string;
    }>('/saas/contacts/imports/process', body),
  syncWhatsApp: () =>
    api.post<{ ok: boolean; synced_contacts: number; message: string }>('/saas/contacts/imports/sync-whatsapp'),
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

/* ── Growth Tools: Social Automations & Coupons ────────────────────────── */
export interface CommentRule {
  id: string;
  platform: 'instagram' | 'facebook';
  keyword: string;
  reply_comment: string;
  send_dm: string;
  active: boolean;
}

export interface CouponItem {
  id: number;
  code: string;
  discount_type: 'percent' | 'fixed';
  discount_value: number;
  applies_to: string;
  max_uses?: number | null;
  used_count: number;
  valid_until?: string | null;
  is_active: boolean;
  created_at?: string;
}

export interface GrowthLinkItem {
  id: string;
  name: string;
  phone: string;
  message: string;
  tags: string[];
  wa_url: string;
  short_url: string;
  qr_code: string;
  clicks: number;
  created_at: string;
}

export const growthToolsApi = {
  getCommentRules: () => api.get<{ ok: boolean; rules: CommentRule[] }>('/saas/social/rules'),
  saveCommentRules: (rules: CommentRule[]) => api.post<{ ok: boolean; rules: CommentRule[] }>('/saas/social/rules', { rules }),
  listCoupons: () => api.get<{ coupons: CouponItem[] }>('/saas/coupons/'),
  createCoupon: (body: {
    code: string;
    discount_type: 'percent' | 'fixed';
    discount_value: number;
    max_uses?: number | null;
    valid_until?: string | null;
  }) => api.post<{ ok: boolean; id: number; code: string }>('/saas/coupons/', body),
  deleteCoupon: (id: number) => api.delete<{ ok: boolean }>(`/saas/coupons/${id}`),
  listLinks: () => api.get<{ links: GrowthLinkItem[] }>('/saas/growth/links'),
  createLink: (body: { name: string; phone: string; message: string; tags?: string[] }) =>
    api.post<{ ok: boolean; link: GrowthLinkItem }>('/saas/growth/links', body),
  deleteLink: (id: string) => api.delete<{ ok: boolean }>(`/saas/growth/links/${id}`),
};
