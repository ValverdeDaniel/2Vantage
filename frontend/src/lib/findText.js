/*
 * Finding text the way the Advisor's finder does (plan.md §8.14, §8.16; F14, E61; the old shared/findText.js), shared
 * with Find on Documents. Pure.
 *
 * Every word typed has to match somewhere, ignoring case; a word matches as typed, or as its letters and digits alone
 * (so "h1234001" finds "H1234-001" and "1500" finds "$1,500"). A word with no letter or digit (a dash, a slash) is
 * punctuation, not a search: it is dropped, so a query of separators alone finds everything, as an empty one does.
 * Carrier nicknames ("UHC") are the Advisor finder's own fold (deal/advisor/board/finder.js, OQ14).
 */

export const lettersAndDigits = (text) => String(text ?? '').replace(/[^\p{L}\p{N}]+/gu, '');

/** The query's words, lower-cased, punctuation-only words dropped. */
export function findWords(query) {
  return String(query || '')
    .toLowerCase()
    .split(/\s+/)
    .filter((word) => lettersAndDigits(word) !== '');
}

/** One searchable text: {plain, bare}, or null when blank. */
export function findField(value) {
  const plain = String(value ?? '').trim().toLowerCase();
  return plain ? { plain, bare: lettersAndDigits(plain) } : null;
}

/** findField over several texts, blanks dropped. */
export const findFields = (...values) => values.map(findField).filter(Boolean);

/** Does one word match one of the fields, as typed or as its letters and digits? */
export function wordMatches(fields, word) {
  const bare = lettersAndDigits(word);
  return fields.some((field) => field.plain.includes(word) || (bare !== '' && field.bare.includes(bare)));
}

/** Does every word match somewhere in the fields? */
export function findMatches(fields, words) {
  return words.every((word) => wordMatches(fields, word));
}
