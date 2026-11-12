/*
 * The Advisor's choices kept per browser (plan.md §8.14; F1, F5, F34, F37): the view, the line, the board's layout
 * and ▦ Pages, under the old key `vantage.bnf.advisor`. Not per deal, so an unavailable view or a line the deal does not have
 * falls back rather than drawing nothing. `?view=` and `?line=` win over the kept choice. Pure.
 *
 * Views (F1): Quote comparison, "As quoted" (one scanned quote as printed, F42; slice 21: offered only once a read
 * has landed a printed table), the Proposal builder (slice 25; J17) and the Export viewer, last, as the old app put it
 * (slice 28; F3). The Stop-loss analysis pill, second as the old app put it, shows only when the deal has a stop-loss
 * line, even with no plans yet (F2; slice 36); Unleashed waits (F4). The Export viewer's file is kept here too, as
 * the old `exportFile`, and `?file=` wins (F136); the viewer decides which files it can show.
 */

export const PREFS_KEY = 'vantage.bnf.advisor';

export const VIEWS = [
  { key: 'quotes', label: 'Quote comparison', hint: 'Filter, sort and shortlist the quoted plans' },
  {
    key: 'stop-loss',
    label: 'Stop-loss analysis',
    hint: 'The reinsurance verdict board — maximum annual liability, lasers, and the analysis workbook',
  },
  {
    key: 'quoted',
    label: 'As quoted',
    hint: "One scanned quote as the carrier printed it: its plans in the file's column order, its rows as printed",
  },
  {
    key: 'build',
    label: 'Proposal builder',
    hint: 'Which quote from each carrier, what the client sees, and the executive summary',
  },
  {
    key: 'export',
    label: 'Export viewer',
    hint: 'The client spreadsheet and PowerPoint as they will export, before you download them',
  },
];
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

/**
 * The views this deal offers: every built view, "As quoted" only when the deal has a printed table (`quoted`, the
 * `plans/as-quoted/` files; F42), and the Stop-loss analysis only when the deal has the stop-loss line (`stopLossLine`,
 * /api/meta/'s `stop_loss.line`; F2), so a pill never opens nothing.
 */
export function offeredViews(lines, quoted, stopLossLine) {
  return VIEWS.filter(
    (view) =>
      (view.key !== 'quoted' || (quoted?.length ?? 0) > 0) &&
      (view.key !== 'stop-loss' || (Boolean(stopLossLine) && lines.some((row) => row.line === stopLossLine))),
  );
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

/** 'grid' (the board) or 'pages' (▦ Pages, "What the client will see"; slice 14), as the old app kept it. */
export function chooseLayout(kept) {
  return kept === 'pages' ? 'pages' : 'grid';
}

/** The Export viewer's file as asked for: the URL's, else the one kept (F136); the viewer resolves what it shows. */
export function chooseFileWanted(param, kept) {
  return param || kept || '';
}
