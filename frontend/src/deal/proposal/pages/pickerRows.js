/*
 * The plan picker's list (plan.md §8.14; F45, F46, J8, J9, J10; the old PlanPicker.jsx at 7385bb3). Pure.
 *
 * Two parts: what is on the proposal, in the client's order (the payload's `presented_ids`), then every other plan on
 * the line as the line orders it (`others`). Typing narrows both by the Advisor's finder rule (src/lib/findText.js over
 * the `plans/find/` index, carrier nicknames included). A plan that cannot go in the spot stays listed, greyed, with
 * the reason in the server's words: a current plan or a priced version (`why_not`), a renewal that stays beside its
 * plan (`stays_words`), a full line (`full_words`). Which of them applies to this spot follows quotes/slots.py: on a
 * line with two or more current plans a pick trades `replaces` sets, and a renewal never changes its plan.
 */

import { findFields, findTerms, termMatches } from '../../../lib/findText';

export const MAX_ROWS = 60;

const sameLinks = (a = [], b = []) => {
  const x = [...a].sort((p, q) => p - q);
  const y = [...b].sort((p, q) => p - q);
  return x.length === y.length && x.every((id, i) => id === y[i]);
};

/** {plan id: place} to search: the finder's texts for the line's plans (name, plan number, carrier, network, codes). */
export function searchPlaces(index, line) {
  const places = new Map();
  for (const entry of index?.plans ?? []) {
    if (entry.line === line) places.set(entry.id, { fields: findFields(...(entry.texts ?? [])), carrier: entry.carrier });
  }
  return places;
}

/** [{plan, on}] in the picker's order, narrowed by `query` (`forms`: carrierForms from /api/meta/ carriers). */
export function pickerEntries(payload, query, places = new Map(), forms = new Map()) {
  const terms = findTerms(query, forms);
  const byId = new Map((payload?.plans ?? []).map((plan) => [plan.plan_id, plan]));
  const place = (plan) => places.get(plan.plan_id) ?? { fields: findFields(plan.carrier, plan.name, plan.words) };
  const matches = (plan) => terms.every((term) => termMatches(place(plan), term));
  const on = (payload?.presented_ids ?? []).map((id) => byId.get(id)).filter(Boolean);
  return [
    ...on.filter(matches).map((plan) => ({ plan, on: true })),
    ...(payload?.others ?? []).filter(matches).map((plan) => ({ plan, on: false })),
  ];
}

/**
 * Why `plan` cannot go here, in words, or null. `spot`: the column picked over (a pick), or null for "＋ Add a plan"
 * with `beside` (the current plan chosen under Replacing:, or null).
 */
export function blockedWhy(plan, { spot = null, beside = null, payload }) {
  if (spot && plan.plan_id === spot.plan_id) return 'Here now';
  if (plan.why_not) return plan.why_not;
  const several = Boolean(payload?.several);
  const target = spot ? spot.links : beside != null ? [beside] : null;
  if (several && plan.stays_with != null && target && !sameLinks(plan.links, target)) return plan.stays_words;
  if (spot && several && spot.stays_with != null && plan.on && !sameLinks(plan.links, spot.links)) {
    return 'The renewal here stays beside its plan';
  }
  if (!spot && !plan.on && payload?.full_words) return payload.full_words;
  return null;
}

/** The words under the search box. */
export function pickerNote({ spot = null, beside = null, payload, lineLabel }) {
  if (spot) {
    const renewalPage = (payload?.pages ?? []).find((page) => page.n === spot.page)?.part === 'renewal';
    if (renewalPage && spot.stays_with != null) {
      return 'Replacing the renewal takes down the renewal page: each current plan then gets its own page.';
    }
    return (
      `Pick the plan to show in place of ${spot.name}. A plan already on the proposal trades places with it; ` +
      'any other replaces it.'
    );
  }
  if (payload?.nothing_starred) {
    return (
      `Nothing is starred, so every ${lineLabel} quote already prints. Adding one moves it last among the plans ` +
      'compared with the current plan you pick.'
    );
  }
  const lands = payload?.landing?.[payload?.several && beside != null ? String(beside) : ''] ?? '';
  return `Add a plan to the ${lineLabel} proposal. ${lands ? `${lands} ` : ''}↑↓ move, Enter picks, Esc closes.`;
}
