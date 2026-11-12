// The Marketing readiness checklist's pure rules (plan.md §8.9; B25–B27), ported from old Vantage 891f1b3
// `market/MarketingChecklist.jsx`: the meter, each row's status badge and controls, the subtitle, and the card's
// remembered collapse. The items, their words and their states come from the server (`intake.checklist`). Vitest pins
// these (checklistModel.test.js).

const DERIVED = ['census', 'coverage_intent']; // their escape is Market anyway (B34): no tick, no override

/** "4/6 ready" and its percent, coloured as the old meter: green when clear, amber from 60 %, else rose. */
export function meterOf(checklist) {
  const required = checklist?.required || 0;
  const done = checklist?.done || 0;
  const pct = required ? Math.round((done / required) * 100) : 100;
  const cls = checklist?.all_clear ? 'bb-green' : pct >= 60 ? 'bb-amber' : 'bb-rose';
  return { done, required, pct, cls };
}

/** The row's status cell: {check: true} for a done row, else a badge {text, cls}. */
export function statusOf(item) {
  if (item.auto_waived) return { text: 'Not needed', cls: 'bb-badge-muted' };
  if (item.waived) return { text: 'Waived', cls: 'bb-badge-muted' };
  if (item.status === 'offer') return { text: 'Optional', cls: 'bb-badge-muted' };
  if (item.forced) return { text: 'Re-asked', cls: 'bb-badge-amber' };
  if (item.done) return { check: true };
  return { text: 'Missing', cls: 'bb-badge-rose' };
}

/**
 * Which controls a row offers (the old card's rules):
 *   attach — ⬆ Attach a file of the item's kind (a document item, not waived, not an offer);
 *   tick — 'On file' (a document) or 'Confirmed' (an attested item), with the same conditions;
 *   override — 'undo' (waived or re-asked by a person), 'still' (Still needed ▸, on a done row) or 'notNeeded'; none
 *   on the two derived items, an offer, or a row that reads Not needed on its own (its switch is the coverage card).
 */
export function controlsOf(item) {
  const isDoc = item.satisfy === 'document';
  const isAttest = item.satisfy === 'attest';
  const open = !item.waived && !item.optional;
  const overridable = !DERIVED.includes(item.key) && !item.optional && !item.auto_waived;
  let override = null;
  if (overridable) override = item.waived || item.forced ? 'undo' : item.done ? 'still' : 'notNeeded';
  return {
    attach: isDoc && open,
    tick: (isDoc || isAttest) && open ? (isDoc ? 'On file' : 'Confirmed') : null,
    override,
  };
}

/** "51–99 enrolled · 60 enrolled — what carriers need before we market." (the head's subtitle). */
export function subtitleOf(checklist, sentAt) {
  const enrolled = checklist?.enrolled || '—';
  const tail = sentAt ? 'what this group owed at market. Still editable.' : 'what carriers need before we market.';
  return `${checklist?.tier_label || ''} · ${enrolled} enrolled${checklist?.estimate ? ' (estimate)' : ''} — ${tail}`;
}

// Put away per deal, in this browser: the old card's own key; an entry means collapsed, anything else reads open.
const PREFS_KEY = 'vantage.bnf.checklist';

function read(storage) {
  try {
    return JSON.parse(storage?.getItem(PREFS_KEY)) || {};
  } catch {
    return {};
  }
}

export function isCollapsed(storage, dealId) {
  return read(storage)[String(dealId)] === true;
}

export function rememberCollapsed(storage, dealId, collapsed) {
  try {
    const next = { ...read(storage) };
    if (collapsed) next[String(dealId)] = true;
    else delete next[String(dealId)];
    storage?.setItem(PREFS_KEY, JSON.stringify(next));
  } catch {
    // a blocked storage never breaks the card
  }
}

/** The "Required to market" banner's tail (B9): the gate's parts beyond the questions, in the old words. */
export function bannerTail(ready) {
  if (!ready) return '';
  const parts = [];
  if (!ready.contacts_ok) parts.push('HR contact');
  if (!ready.bor_on_file) parts.push('Signed BOR');
  if (!ready.census_ok) parts.push('Census');
  return parts.map((part) => ` · ${part}`).join('');
}
