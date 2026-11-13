/*
 * The receipt's pure rules (plan.md §8.20; L98–L100; the old roadmap's N1; slice 59).
 * - `opensOnReceipt(page)`: a submitted link opens on its receipt — unless a follow-up waits for the client's answer,
 *   when it opens on the form, follow-ups first (the old portal: "A submitted link with a follow-up still open opens on
 *   its follow-up page instead of the thank-you card", D-142).
 * - `sentWords(at)`: "Sent Nov 12, 2026 at 3:04 PM", in the client's own time.
 * The receipt itself (what went, by section) is the server's (`payload.receipt`): the browser only shows it.
 */

export function followUpWaits(page) {
  return (page?.follow_ups || []).some((card) => card.needs_answer && !card.answered);
}

export function opensOnReceipt(page) {
  return Boolean(page?.submitted_at) && !followUpWaits(page);
}

export function sentWords(at, { locale = 'en-US', timeZone } = {}) {
  if (!at) return '';
  const when = new Date(at);
  const day = when.toLocaleDateString(locale, { month: 'short', day: 'numeric', year: 'numeric', timeZone });
  const time = when.toLocaleTimeString(locale, { hour: 'numeric', minute: '2-digit', timeZone });
  return `Sent ${day} at ${time}`;
}
