/**
 * Analytics fire-and-forget — POST /api/telemetry/event.
 * Falhas são silenciosas (telemetria não quebra UX).
 *
 * Eventos servidor-only (signup_completed, first_message_sent) são
 * disparados pelo backend; aqui só vai o que vem do frontend.
 */
type EventName =
  | 'onboarding_step_completed'
  | 'page_viewed'
  | 'feature_used'
  | 'reading_generated'
  | 'ritual_completed'
  | 'dream_logged'
  | 'journal_entry'
  | 'community_post'
  | 'content_generated'
  | 'share_clicked'
  | 'upsell_clicked';

export function track(event: EventName, props: Record<string, unknown> = {}): void {
  // sendBeacon é resilient a unload/navigation; fallback fetch.
  try {
    const body = JSON.stringify({ event, props });
    if (navigator.sendBeacon) {
      const blob = new Blob([body], { type: 'application/json' });
      const ok = navigator.sendBeacon('/api/telemetry/event', blob);
      if (ok) return;
    }
    fetch('/api/telemetry/event', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body,
      keepalive: true,
    }).catch(() => {});
  } catch {
    // engole — telemetria nunca falha visualmente
  }
}
