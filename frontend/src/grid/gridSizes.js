/*
 * Where a grid's Excel-style sizes are kept (plan.md §8.21; F36, D-160): per user, in this browser, across every
 * deal, under `vantage.bnf.gridsizes.<user>` as {<grid>: {planW, rows: {<row key>: px}}}. Checked on read: a value
 * out of range is dropped. Nothing here reaches a client file. `storage` is window.localStorage in the browser.
 */

export const FIT_PLANS = 5;
export const MIN_PLAN_PX = 100;
export const MAX_PLAN_PX = 640;
export const MIN_ROW_PX = 33; // one line of 13 px text plus the cell's padding
export const MAX_ROW_PX = 480;
export const LEAD_COL_PX = 210; // the frozen label column (.bnf-benefit-col: min-width 190 + padding)
export const EMPTY_SIZES = Object.freeze({ planW: null, rows: Object.freeze({}) });

export const storeKey = (userId) => `vantage.bnf.gridsizes.${userId}`;
const inRange = (n, lo, hi) => typeof n === 'number' && Number.isFinite(n) && n >= lo && n <= hi;
export const clamp = (n, lo, hi) => Math.max(lo, Math.min(hi, n));

function readAll(storage, userId) {
  try {
    const value = JSON.parse(storage.getItem(storeKey(userId)) || 'null');
    return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
  } catch {
    return {};
  }
}

/** One grid's sizes for a user, or EMPTY_SIZES. */
export function readSizes(storage, userId, grid) {
  if (userId == null || !storage) return EMPTY_SIZES;
  const mine = readAll(storage, userId)[grid];
  if (!mine || typeof mine !== 'object') return EMPTY_SIZES;
  const rows = {};
  for (const [key, px] of Object.entries(mine.rows && typeof mine.rows === 'object' ? mine.rows : {})) {
    if (inRange(px, MIN_ROW_PX, MAX_ROW_PX)) rows[key] = Math.round(px);
  }
  return { planW: inRange(mine.planW, MIN_PLAN_PX, MAX_PLAN_PX) ? Math.round(mine.planW) : null, rows };
}

/** Keep one grid's sizes (EMPTY_SIZES removes them); quiet when storage is unavailable. */
export function writeSizes(storage, userId, grid, sizes) {
  if (userId == null || !storage) return;
  try {
    const all = readAll(storage, userId);
    if (sizes.planW == null && !Object.keys(sizes.rows).length) delete all[grid];
    else all[grid] = sizes;
    if (Object.keys(all).length) storage.setItem(storeKey(userId), JSON.stringify(all));
    else storage.removeItem(storeKey(userId));
  } catch {
    /* private mode: the sizes last until the page is left */
  }
}

/** The default plan column width: FIT_PLANS across what the scroller has after the label column. */
export function fitWidth(scrollerWidth) {
  const room = scrollerWidth - LEAD_COL_PX;
  return room > 0 ? Math.max(MIN_PLAN_PX, Math.floor(room / FIT_PLANS)) : null;
}
