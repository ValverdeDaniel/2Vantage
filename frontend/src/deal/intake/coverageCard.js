// The Coverage & marketing intent card's pure rules (plan.md §8.9; B16–B21, B23), ported from old Vantage 891f1b3
// `market/CoverageIntentPanel.jsx` and `CoverageDocPicker.jsx`. Vitest pins them (coverageCard.test.js).

/* The three THIS YEAR columns in the order the row reads. The header words are fixed; a line not in force reads the
 * same choices as "Quote it" and "Present it", which the row's box title carries (`this_year_label`). The words come
 * from /api/meta/'s intake.coverage.this_year. */
export function yearColumns(meta) {
  return meta?.intake?.coverage?.this_year || [];
}

// The card's three states (B20): its class, badge and subtitle.
export const STATES = {
  done: {
    cls: 'bnf-cvg-done',
    badge: '✓ Confirmed',
    sub: 'What they have today, and what we do with each line this year.',
  },
  stale: {
    cls: 'bnf-cvg-stale',
    badge: '⚠ Changed since confirmed',
    sub: 'Coverage or the shopping list changed since this was confirmed — take another look and confirm again.',
  },
  open: {
    cls: 'bnf-cvg-open',
    badge: 'Not confirmed yet',
    sub:
      'What they have today, and what we do with each line this year. ' +
      'This decides which documents we need — confirm it first.',
  },
};

export function cardState(intent) {
  return STATES[intent?.state] || STATES.open;
}

/** The header badge's gaps: "1 unanswered · 2 documents missing". */
export function gapWords(intent) {
  const gaps = [];
  const unanswered = intent?.counts?.unanswered || 0;
  const missing = intent?.documents_missing || 0;
  if (unanswered) gaps.push(`${unanswered} unanswered`);
  if (missing) gaps.push(`${missing} document${missing === 1 ? '' : 's'} missing`);
  return gaps;
}

/** The footer tally: "2 shopping · 1 kept as-is · 0 new · 3/6 documents". */
export function tallyWords(intent) {
  const counts = intent?.counts || {};
  const docs = intent?.documents_expected
    ? ` · ${intent.documents_on_file}/${intent.documents_expected} documents`
    : '';
  return `${counts.shopping || 0} shopping · ${counts.keep || 0} kept as-is · ${counts.new || 0} new${docs}`;
}

/** A select-all header box: 'on' when every eligible row hits, 'mixed' when some do, '' when none, 'off' when no
 *  row is eligible. */
export function headerState(rows, hit) {
  if (!rows.length) return 'off';
  const count = rows.filter(hit).length;
  if (count === rows.length) return 'on';
  return count ? 'mixed' : '';
}

/** The In force header: every row is eligible; an unanswered row counts as not ticked. */
export function inForceState(rows) {
  return headerState(rows, (row) => row.answered && row.in_force);
}

/** A THIS YEAR header: only answered rows are eligible (the row must say whether they have it first). */
export function yearState(rows, key) {
  return headerState(
    rows.filter((row) => row.answered),
    (row) => row.this_year === key,
  );
}

/** The document chips a row shows: every kind for a line in force, else only the kinds on file (showing is not
 *  requiring: `needs_documents` decides what counts as missing). */
export function shownKinds(row, kinds) {
  return row.in_force ? kinds : kinds.filter((kind) => (row.documents?.[kind] || []).length);
}

// ---- the document picker's scope (B21): a file's `lines` [] means every line, never none --------------------------

export const coversEverything = (doc) => !(doc.lines || []).length;

/** The PATCH that attaches `doc` to `line` as `kind` (re-filed in the same request), or null when it already is. */
export function attachChanges(doc, line, kind) {
  const changes = {};
  const scope = doc.lines || [];
  if (coversEverything(doc)) changes.lines = [line];
  else if (!scope.includes(line)) changes.lines = [...scope, line];
  if (doc.kind !== kind) changes.kind = kind;
  return Object.keys(changes).length ? changes : null;
}

/** The PATCH that ticks `key` on or off the file's scope, or null for the last line (never down to zero). */
export function toggleLineChanges(doc, key, allLines) {
  const scope = doc.lines || [];
  if (coversEverything(doc)) return { lines: allLines.filter((line) => line !== key) };
  if (scope.includes(key)) return scope.length === 1 ? null : { lines: scope.filter((line) => line !== key) };
  return { lines: [...scope, key] };
}

// ---- collapse, remembered per deal (B23): the old app's key; an entry means collapsed ---------------------------

export const PREFS_KEY = 'vantage.bnf.coverage';

function read(storage) {
  try {
    const parsed = JSON.parse(storage?.getItem(PREFS_KEY) || '{}');
    return parsed && typeof parsed === 'object' ? parsed : {};
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
