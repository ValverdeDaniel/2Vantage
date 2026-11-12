/*
 * The Change history card's groups (plan.md §8.16; E73, E74; the old benefits/history.py and ChangeHistoryCard): the
 * deal's Activity rows, newest first, grouped by person into spans of at most 30 minutes, each summed up as
 * "3 changes · 1 file action · 12 values reviewed". Pure: feed rows in ({id, at, actor, actor_kind, area, action,
 * summary, count, document_id, can_revert, reverted}), groups out.
 */

export const WINDOW_MINUTES = 30;
const WINDOW_MS = WINDOW_MINUTES * 60 * 1000;
const REVIEW = 'marked';
const FILES = 'documents';

const plural = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`;

/** 'review' (a review's marks), 'file' (a file uploaded, edited, removed or restored) or 'change'. */
export function kindOf(row) {
  if (row.action === REVIEW) return 'review';
  if (row.area === FILES) return 'file';
  return 'change';
}

/** [{actor, kind, start, end, items}] from rows newest first: one person's rows within 30 minutes of the group's last. */
export function groupRows(rows) {
  const groups = [];
  for (const row of rows) {
    const at = new Date(row.at).getTime();
    const last = groups[groups.length - 1];
    const same = last && last.actor === row.actor && last.kind === row.actor_kind;
    if (same && new Date(last.end).getTime() - at <= WINDOW_MS) {
      last.items.push(row);
      last.start = row.at;
    } else {
      groups.push({ actor: row.actor, kind: row.actor_kind, start: row.at, end: row.at, items: [row] });
    }
  }
  return groups;
}

/** "3 changes · 1 file action · 12 values reviewed", or "2 events". */
export function groupSummary(group) {
  let changes = 0;
  let files = 0;
  let reviewed = 0;
  for (const row of group.items) {
    const kind = kindOf(row);
    if (kind === 'review') reviewed += row.count || 1;
    else if (kind === 'file') files += 1;
    else changes += row.count || 1;
  }
  const parts = [];
  if (changes) parts.push(plural(changes, 'change'));
  if (files) parts.push(plural(files, 'file action'));
  if (reviewed) parts.push(`${plural(reviewed, 'value')} reviewed`);
  return parts.length ? parts.join(' · ') : plural(group.items.length, 'event');
}

/** The icon a row wears: ✓ a review, ⤓ an upload, 🗑 a removal, ✎ any other edit. */
export function rowIcon(row) {
  const kind = kindOf(row);
  if (kind === 'review') return '✓';
  if (kind === 'file' && row.action === 'created') return '⤓';
  if (kind === 'file' && /^Removed/.test(row.summary || '')) return '🗑';
  return '✎';
}
