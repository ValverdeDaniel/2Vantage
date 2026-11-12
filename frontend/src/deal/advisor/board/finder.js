/*
 * The plan finder (plan.md §8.14; F14–F17, OQ14; the old planFinder.js and AdvisorTab's FIND-1). Pure.
 *
 * It searches the index `plans/find/` serves: every line's plans, each with its name, plan number, carrier, network,
 * plan type and codes, and the carrier its name means (the server's one matcher). Every typed word must match one of
 * those texts (src/lib/findText's word rule); a run of words that names a carrier — its name or one of its aliases
 * from /api/meta/ carriers, never a list here — also matches every plan of that carrier, so "UHC" finds
 * UnitedHealthcare and "BCBS" Florida Blue (OQ14), and nothing else. Current plans are pinned on their board whatever
 * is typed, so they never count as hits. The hits per line give "Also matches 2 on Dental" (F15) and the empty
 * board's sentence (F17).
 */

import { findFields, findWords, lettersAndDigits, wordMatches } from '../../../lib/findText';

const squash = (text) => lettersAndDigits(String(text ?? '').toLowerCase());

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

/** The index ready to search: each entry's texts as find fields. */
export function prepareIndex(plans = []) {
  return plans.map((entry) => ({ ...entry, fields: findFields(...(entry.texts ?? [])) }));
}

/** Does one prepared entry answer every term? */
export function entryMatches(entry, terms) {
  return terms.every((term) => (term.carrier && entry.carrier === term.carrier) || wordMatches(entry.fields, term.word));
}

/**
 * The finder's answer: {query, active, ids (the quotes that answer), byLine: Map(line → [ids])}. Inactive (nothing
 * typed, or only punctuation) means every plan shows.
 */
export function runFinder(index, query, forms) {
  const terms = findTerms(query, forms);
  const ids = new Set();
  const byLine = new Map();
  if (terms.length) {
    for (const entry of index) {
      if (entry.current || !entryMatches(entry, terms)) continue;
      ids.add(entry.id);
      if (!byLine.has(entry.line)) byLine.set(entry.line, []);
      byLine.get(entry.line).push(entry.id);
    }
  }
  return { query: String(query ?? '').trim(), active: terms.length > 0, ids, byLine };
}

/** The hits on `line`. */
export function hitsOn(finder, line) {
  return finder.byLine.get(line) ?? [];
}

/** "Also matches": [{line, label, count}] for the deal's other lines with hits, in the deal's line order. */
export function otherHits(finder, line, lines) {
  if (!finder.active) return [];
  return lines
    .filter((row) => row.line !== line && hitsOn(finder, row.line).length > 0)
    .map((row) => ({ line: row.line, label: row.label, count: hitsOn(finder, row.line).length }));
}

const plansWord = (count) => `${count} plan${count === 1 ? '' : 's'}`;

/**
 * What the empty board says (F17): why nothing shows. Nothing here but matches elsewhere names those lines; matches
 * here hidden by the other filters say so; otherwise the plain sentence.
 */
export function emptyNote({ finder, line, lineLabel, others = [], quoteCount }) {
  if (!quoteCount) return `No quoted plans on ${lineLabel} yet — only the current plans.`;
  if (!finder?.active) return 'No plans match the current filters.';
  const here = hitsOn(finder, line).length;
  if (!here && others.length) {
    const named = others.map((hit) => `${plansWord(hit.count)} on ${hit.label}`);
    const elsewhere = named.length > 1 ? `${named.slice(0, -1).join(', ')} and ${named.at(-1)}` : named[0];
    const verb = others.length === 1 && others[0].count === 1 ? 'does' : 'do';
    return `Nothing on ${lineLabel} matches “${finder.query}”, but ${elsewhere} ${verb}. Pick a line under the search box.`;
  }
  if (here) {
    const one = here === 1;
    return (
      `${plansWord(here)} on ${lineLabel} ${one ? 'matches' : 'match'} “${finder.query}”, but the other filters ` +
      `hide ${one ? 'it' : 'them'}. Clear resets them.`
    );
  }
  return `Nothing matches “${finder.query}”.`;
}
