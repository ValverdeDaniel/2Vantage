// The data confidence's words (plan.md §8.6; M83–M92; old Vantage 891f1b3 `DataConfidence.jsx`): the counts on each
// file, the buttons' labels, the toasts, a marked row's meta line, where a row opens and the re-read's result line.
// Pure: Vitest pins them. Every count is the server's; nothing here works one out but the old labels' arithmetic.
import { formatDate } from '../../../lib/format';

export const plural = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`;

/** "12 values · 3 confirmed" under a file's name. */
export function docMeta(doc) {
  return `${plural(doc.values, 'value')} · ${doc.confirmed} confirmed`;
}

/** The warnings Ignore takes on a file: its open warnings not flagged ⚑ (the old "Ignore N warnings"). */
export function ignoreCount(doc) {
  return Math.max(0, (doc.to_review ?? 0) - (doc.check ?? 0));
}

/** What Confirm all asks first (M88). */
export function confirmQuestion(doc) {
  const left = doc.values - doc.confirmed;
  return `Confirm ${plural(left, 'value')} from this file?`;
}

const DONE = { approve: 'approved', ignore: 'ignored', check: 'flagged as needing checking', clear: 'unmarked' };
const VERB = { approve: 'approve', ignore: 'ignore', check: 'flag', clear: 'undo' };

/**
 * The toast after a review (the old `reviewToast`): Confirm all on a file says "Confirmed 12 values"; a file's other
 * buttons "3 values ignored on <file>"; a row's "1 value approved"; nothing done, "Nothing to ignore on <file>".
 */
export function markToast(action, count, where = '') {
  const on = where ? ` on ${where}` : '';
  if (action === 'approve' && where) return count ? `Confirmed ${plural(count, 'value')}` : `Nothing to confirm${on}`;
  if (!count) return `Nothing to ${VERB[action] || 'review'}${on}`;
  return `${plural(count, 'value')} ${DONE[action] || 'reviewed'}${on}`;
}

/** "Dana Example · Nov 12, 2026 · quote.pdf" under a marked row. */
export function markedMeta(row) {
  return [row.by, row.at && formatDate(row.at), row.doc?.name].filter(Boolean).join(' · ');
}

/** Where a marked row's value lives: its tab, a form's own page for a questionnaire answer. */
export function rowPath(dealId, row) {
  const base = `/deals/${dealId}/${row.tab}`;
  return row.form ? `${base}?form=${encodeURIComponent(row.form)}` : base;
}

/** The re-read's result line, in parts: {checked, agreed, differ, notFound, at} or null before one finished. */
export function recheckResult(last) {
  if (!last || last.status !== 'done') return null;
  const { checked, agreed, differ, not_found: notFound } = last.counts || {};
  return {
    head: `Re-read ${plural(checked ?? 0, 'scanned value')} — `,
    agreed: `${agreed ?? 0} agreed`,
    differ: differ ? `${differ} disagree` : '',
    notFound: notFound ? `${notFound} not found` : '',
    at: last.at ? formatDate(last.at) : '',
  };
}

/** Why "Double-check with AI" is off, or '' when it may run (M92). */
export function recheckBlocked({ claude, values, running }) {
  if (!claude) return 'Needs the Claude API — no ANTHROPIC_API_KEY is configured.';
  if (!values) return 'Nothing on this deal came from a scan, so there is nothing to re-read.';
  if (running) return 'Claude is busy with another read on this deal; the re-read can start once it ends.';
  return '';
}
