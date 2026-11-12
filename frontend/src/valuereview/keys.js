/*
 * The review keys (plan.md §8.16; E55, D124; the old useReviewHotkeys.js): A approves, I ignores, C flags as needing
 * checking, U clears a mark and F finds the value in its file, for whatever is selected on the List (and, from slice
 * 23, the Grid). Pure: which action a key press means, or null.
 *
 * A key never acts while someone types (an input, a text area, a select, anything editable), with Ctrl, Cmd or Alt
 * held, on a held-down repeat, or when another handler already took it.
 */

export const REVIEW_KEYS = { a: 'approve', i: 'ignore', c: 'check', u: 'clear', f: 'find' };

export function isTyping(el) {
  if (!el || el.nodeType !== 1) return false;
  if (el.isContentEditable) return true;
  const tag = el.tagName;
  return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT';
}

/** The action a keydown event means for `keys`, or null. */
export function keyAction(event, keys = REVIEW_KEYS) {
  if (!event || event.defaultPrevented || event.repeat || event.isComposing) return null;
  if (event.ctrlKey || event.metaKey || event.altKey) return null;
  const action = keys[String(event.key || '').toLowerCase()];
  if (!action || isTyping(event.target)) return null;
  return action;
}
