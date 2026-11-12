/*
 * One page of "What the client will see" laid out from the pages payload (plan.md §8.14; F37–F39, J49, J50; the old
 * ProposalPages.jsx at 7385bb3). Pure. The server splits the pages, words every column and formats every cell
 * (proposals/pages_read.py): this only puts them in the page's order, marks a plan shown again, groups the rows under
 * their headings (All columns) and folds a line with nothing starred to its first two pages.
 */

/** A blank cell reads as a dash. */
export const cellText = (text) => (text === null || text === undefined || text === '' ? '—' : text);

/** {plan id: column facts} from the payload's `plans`. */
export function columnsById(payload) {
  return new Map((payload?.plans ?? []).map((plan) => [plan.plan_id, plan]));
}

/**
 * The page's columns left to right: [{plan, place (from 1), repeated}]. A plan is shown again when the page repeats it
 * (a current plan on a later page) or it first showed on an earlier page; its tools stay where it first shows.
 */
export function pageColumns(page, byId) {
  return page.plan_ids
    .map((id) => byId.get(id))
    .filter(Boolean)
    .map((plan, i) => ({
      plan,
      place: i + 1,
      repeated: (page.repeat_ids ?? []).includes(plan.plan_id) || plan.page !== page.n,
    }));
}

/**
 * The rows under Monthly premium and Change vs current: [{heading, rows: [{key, label, cells: [text per column]}]}].
 * Consecutive rows with one `section` share a heading (All columns names the line's groups; other tabs have none).
 */
export function pageSections(rows, plans) {
  const out = [];
  for (const row of rows ?? []) {
    const heading = row.section || null;
    if (!out.length || out.at(-1).heading !== heading) out.push({ heading, rows: [] });
    out.at(-1).rows.push({
      key: row.key,
      label: row.label,
      cells: plans.map((plan) => cellText(row.cells?.[String(plan.plan_id)])),
    });
  }
  return out;
}

/** With nothing starred and more than two pages, the first two until "Show every page (N)" (F38). */
export function shownPages(pages, nothingStarred, showAll) {
  const folded = Boolean(nothingStarred) && pages.length > 2 && !showAll;
  return { pages: folded ? pages.slice(0, 2) : pages, folded, foldable: Boolean(nothingStarred) && pages.length > 2 };
}

/** "Page 2 of 3", the page's words, and "4 of 6 columns · full". */
export function pageHead(page, count, perPage) {
  const held = page.plan_ids.length;
  return {
    title: `Page ${page.n} of ${count}`,
    label: page.label,
    count: `${held} of ${perPage} columns${page.full ? ' · full' : ''}`,
  };
}
