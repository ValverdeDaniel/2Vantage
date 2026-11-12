/*
 * Finding text the way the Advisor's finder does (plan.md §8.14, §8.16; F14, E61–E64; the old shared/findText.js),
 * shared with Find on Documents. Pure.
 *
 * Every word typed has to match somewhere, ignoring case; a word matches as typed, or as its letters and digits alone
 * (so "h1234001" finds "H1234-001" and "1500" finds "$1,500"). A word with no letter or digit (a dash, a slash) is
 * punctuation, not a search: it is dropped, so a query of separators alone finds everything, as an empty one does.
 *
 * Carrier nicknames (OQ14): a run of words that squashes to a carrier's name or alias (/api/meta/ carriers, never a
 * list here) is one term that also matches every place whose carrier is that carrier — the server's one matcher
 * names it (`plans/find/`), so "UHC" finds UnitedHealthcare and never United Concordia, on the Advisor and on
 * Documents alike.
 *
 * Documents' Find reports a hit at the most specific place that explains it (the old `findHit`): a place is
 * {fields, carrier?} — a plan's head (its finder texts and carrier), a row's label, or one value.
 */

export const lettersAndDigits = (text) => String(text ?? '').replace(/[^\p{L}\p{N}]+/gu, '');

const squash = (text) => lettersAndDigits(String(text ?? '').toLowerCase());

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

/** {squashed form: carrier key} from meta's carriers: each one's key, name and aliases. */
export function carrierForms(carriers = []) {
  const forms = new Map();
  for (const carrier of carriers) {
    for (const form of [carrier.key, carrier.name, ...(carrier.aliases ?? [])]) {
      const squashed = squash(form);
      if (squashed && !forms.has(squashed)) forms.set(squashed, carrier.key);
    }
  }
  return forms;
}

/**
 * The query as terms: [{word, carrier?}]. The longest run of words, from each word on, that squashes to a carrier's
 * name or alias becomes one carrier term ("blue cross blue shield"); every other word stays a word.
 */
export function findTerms(query, forms = new Map()) {
  const words = findWords(query);
  const terms = [];
  let at = 0;
  while (at < words.length) {
    let end = words.length;
    for (; end > at; end -= 1) {
      if (forms.has(words.slice(at, end).map(squash).join(''))) break;
    }
    if (end > at) {
      terms.push({ word: words.slice(at, end).join(' '), carrier: forms.get(words.slice(at, end).map(squash).join('')) });
      at = end;
    } else {
      terms.push({ word: words[at] });
      at += 1;
    }
  }
  return terms;
}

/** Does one term match a place ({fields, carrier?}): its carrier, or one of its texts? */
export function termMatches(place, term) {
  if (term.carrier && place.carrier === term.carrier) return true;
  return wordMatches(place.fields, term.word);
}

/** Does a place answer every term? A place with no texts and no carrier answers nothing. */
export function placeMatches(place, terms) {
  return terms.length > 0 && terms.every((term) => termMatches(place, term));
}

/**
 * Does a VALUE answer the terms, given its row's label and its column's head (each a place)? A head that answers
 * every term alone is the head's hit ("aetna": one per Aetna plan, not one per Aetna cell), a label the same
 * ("deductible": the Deductible rows). A value is a hit when it answers alone, or when only the three together do
 * ("aetna deductible": the deductible values of the Aetna plans). A blank value is never one.
 */
export function findHit(terms, value, row, col) {
  if (!terms.length || !value.fields.length) return false;
  if (placeMatches(value, terms)) return true;
  if (placeMatches(row, terms) || placeMatches(col, terms)) return false;
  return terms.every((term) => termMatches(value, term) || termMatches(row, term) || termMatches(col, term));
}
