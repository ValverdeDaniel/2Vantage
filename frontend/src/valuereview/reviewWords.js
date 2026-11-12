/*
 * The review's words (plan.md §8.16; E48, E52, E54, D124, D126; the old valueReview.js and DocumentsTab's
 * CONFIRM_WORDS): the toasts after approve, ignore, needs checking and clear, the confirm a key asks above 25 values,
 * and Undo's answer. Pure.
 */

export const ACTION_WORDS = {
  approve: { done: 'approved', verb: 'Approve' },
  ignore: { done: 'ignored', verb: 'Ignore' },
  check: { done: 'flagged as needing checking', verb: 'Needs checking' },
  clear: { done: 'unmarked', verb: 'Undo' },
};

// D-125 / D126: a review key that would act on more values than this asks first; the buttons say their count.
export const CONFIRM_OVER = 25;
const CONFIRM_WORDS = {
  approve: (n) => `Approve ${n} values?`,
  ignore: (n) => `Ignore the AI's warning on ${n} values?`,
  check: (n) => `Flag ${n} values as needing checking?`,
  clear: (n) => `Clear the marks on ${n} values?`,
};

export const plural = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`;

/** The question a key asks before acting on `count` values, or '' when it acts at once. */
export function confirmWords(action, count, { fromKey = false } = {}) {
  if (!fromKey || count <= CONFIRM_OVER) return '';
  return (CONFIRM_WORDS[action] || CONFIRM_WORDS.approve)(count);
}

/** "3 values approved on the 2 ticked plans" — the toast after a review; "Nothing to approve on this file". */
export function reviewToast(action, changed, where = '') {
  const words = ACTION_WORDS[action] || ACTION_WORDS.approve;
  const on = where ? ` on ${where}` : '';
  if (!changed) return `Nothing to ${words.verb.toLowerCase()}${on}`;
  return `${plural(changed, 'value')} ${words.done}${on}`;
}

/** "✓ 3 values approved" — what the last action did, beside its ↶ Undo. */
export function doneText(done) {
  if (!done?.changed) return '';
  const words = ACTION_WORDS[done.action] || ACTION_WORDS.approve;
  return `✓ ${plural(done.changed, 'value')} ${words.done}`;
}

/** Undo's answer: "Undone — 3 values back as before; 1 changed since and was left as it is". */
export function undoneText(restored, skipped = 0) {
  const left = skipped ? `; ${skipped} changed since and ${skipped === 1 ? 'was' : 'were'} left as ${skipped === 1 ? 'it is' : 'they are'}` : '';
  return `Undone — ${plural(restored, 'value')} back as before${left}`;
}

/** How many values a revert's `changes` put back ([{t, k: {key: [after, before]}}]). */
export function restoredCount(changes) {
  return (changes ?? []).reduce((sum, change) => sum + Object.keys(change.k ?? {}).length, 0);
}

/** The strip's target words: "this file", "these 3 files", "the 2 ticked plans", "every plan on Medical". */
export function targetWords({ files = 0, ticked = 0, filtered = null, line = '' } = {}) {
  if (files) return files === 1 ? 'this file' : `these ${files} files`;
  if (ticked) return `the ${plural(ticked, 'ticked plan')}`;
  if (filtered != null) return `the ${plural(filtered, 'plan')} the filters show`;
  return `every plan on ${line}`;
}
