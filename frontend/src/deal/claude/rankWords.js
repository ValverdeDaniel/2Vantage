// What ⚖ Rank plans says (plan.md §8.17, §10.4; D6, D36, D96, F111, OQ44; slice 37; the old WorkWithClaude rank button
// and its strip news). Pure.

/** What the button ranks: the board's line, and only the plans its filters show when it is filtered (OQ44: stars
 *  outside the filter stay). `board` is the Advisor's ({line, shown_ids, total}) or null; `line` the tab's fallback. */
export function rankScope(board, line = '') {
  const filtered = Boolean(board && Array.isArray(board.shown_ids) && board.shown_ids.length < board.total);
  return { line: board?.line || line || '', planIds: filtered ? board.shown_ids : null, filtered };
}

/** The button's words: "⚖ Rank plans", "⚖ Rank filtered (5)", "Ranking…". */
export function rankLabel(scope, ranking) {
  if (ranking) return 'Ranking…';
  return scope.filtered ? `⚖ Rank filtered (${scope.planIds.length})` : '⚖ Rank plans';
}

/** Why the button is off, or what it does (its title). */
export function rankTitle({ locked, guidance, scope }) {
  if (locked) return 'The table is locked from Claude, so it cannot star plans. Unlock it to rank.';
  if (!guidance) return 'Add client guidance first';
  if (!scope.line) return 'Open a line on the Advisor to rank its plans';
  if (scope.filtered) return 'Replaces the stars among the plans the board shows; stars outside the filter stay';
  return 'Replaces the current shortlist on this line, including hand-picked plans';
}

/** The strip after a rank landed: "★ Claude ranked the plans — starred 6 Medical plans". */
export function rankLandedText(news) {
  return `★ Claude ranked the plans — ${news.summary}`;
}

/** What ↶ Undo this run asks first, for a rank. */
export const RANK_UNDO_ASK =
  'The stars this ranking set come off, and the stars it replaced come back with their reasons. If someone has ' +
  'starred or unstarred one of these plans since, Undo is refused.';

export const RANK_UNDONE = 'Undone — the stars are back the way they were before the ranking.';

/** The toast when a rank ends (D36: the old "Shortlist updated"). */
export function rankToast(job) {
  if (job.status === 'failed') return { tone: 'error', text: job.error || 'The ranking failed.' };
  if (job.status !== 'done' || !job.landed?.plan_ids?.length) return null;
  return { tone: 'success', text: `Shortlist updated — ${job.landed.summary}` };
}
