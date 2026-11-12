/*
 * The Advisor's choices kept per browser (plan.md §8.14; F1, F5, F34): the view, the line and the board's layout,
 * under the old key `vantage.bnf.advisor`. Not per deal, so an unavailable view or a line the deal does not have
 * falls back rather than drawing nothing. `?view=` and `?line=` win over the kept choice. Pure.
 *
 * Views (F1): only Quote comparison is built. The Stop-loss analysis pill (only with a stop-loss line, F2), the
 * Proposal builder and the Export viewer join this list with their slices (36, 25, 28); Unleashed waits (F4).
 */

export const PREFS_KEY = 'vantage.bnf.advisor';

export const VIEWS = [{ key: 'quotes', label: 'Quote comparison', hint: 'Filter, sort and shortlist the quoted plans' }];
export const DEFAULT_VIEW = 'quotes';

export function readPrefs(storage) {
  try {
    const value = JSON.parse(storage?.getItem(PREFS_KEY) || 'null');
    return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
  } catch {
    return {};
  }
}

export function writePrefs(storage, patch) {
  try {
    storage?.setItem(PREFS_KEY, JSON.stringify({ ...readPrefs(storage), ...patch }));
  } catch {
    /* private mode: the choice lasts until the page is left */
  }
}

/** The views this deal offers: every built view (a stop-loss one would need the deal's stop-loss line, F2). */
export function offeredViews() {
  return VIEWS;
}

/** The view to show: the URL's, else the kept one, when offered; else Quote comparison. */
export function chooseView(param, kept, offered = VIEWS) {
  const wanted = param || kept;
  return offered.some((view) => view.key === wanted) ? wanted : DEFAULT_VIEW;
}

/** The line to show: the URL's, else the kept one, when the deal has it; else the deal's first line. */
export function chooseLine(param, kept, lines) {
  for (const wanted of [param, kept]) {
    if (wanted && lines.some((row) => row.line === wanted)) return wanted;
  }
  return lines[0]?.line ?? '';
}

/** 'rows' (plans as rows, the board) or 'cols' (transposed, plans as columns). */
export function chooseOrientation(kept) {
  return kept === 'cols' ? 'cols' : 'rows';
}
