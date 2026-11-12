/*
 * One printed page of a tab (plan.md §8.14; J117; the old WorkbookPages.jsx at 891f1b3): which rows and columns it
 * holds (the repeated titles first), the sheet of paper at the stage's width and where the tab sits on it, and the
 * notes about Fit To and a near edge. Where each page breaks is the server's (proposals/viewer/workbook_pages.py).
 * Pure.
 */

const range = (a, b) => Array.from({ length: b - a + 1 }, (_v, i) => a + i);

/** {rows, cols, missing}: the page's rows and columns with the repeated ones, and whether rows past the shown ones
 * would print (a capped tab). */
export function pageCells(info, page, shownRows) {
  if (!page) return { rows: [], cols: [], missing: false };
  const titleRows =
    info.title_rows && page.rows[0] > info.title_rows[1] ? range(info.title_rows[0], info.title_rows[1]) : [];
  const titleCols =
    info.title_cols && page.cols[0] > info.title_cols[1] ? range(info.title_cols[0], info.title_cols[1]) : [];
  const own = range(page.rows[0], page.rows[1]);
  return {
    rows: [...titleRows, ...own].filter((r) => r < shownRows),
    cols: [...titleCols, ...range(page.cols[0], page.cols[1])],
    missing: own.some((r) => r >= shownRows),
  };
}

/** The sheet of paper `stage` pixels wide (at most 1100) and the tab's place on it. A column prints `print_width`
 * wider than it draws while the type keeps its size, so the grid is drawn with wider columns, then scaled. */
export function paperGeometry(info, colPx, cols, stage) {
  const paperW = Math.min(stage || 900, 1100);
  const perIn = paperW / info.paper.w;
  const widen = info.print_width || 1;
  const k = (info.scale / 100) * (perIn / 96);
  const sheetW = cols.reduce((sum, c) => sum + Math.round((colPx[c] || 64) * widen), 0);
  const usableW = (info.paper.w - info.margins.left - info.margins.right) * perIn;
  const centred = info.centered ? Math.max(0, (usableW - sheetW * k) / 2) : 0;
  return {
    paperW,
    paperH: perIn * info.paper.h,
    perIn,
    widen,
    k,
    left: info.margins.left * perIn + centred,
    top: info.margins.top * perIn,
    footerBottom: info.margins.footer * perIn,
    footerSize: (11 * perIn) / 72, // a footer prints at its own size, never scaled with the tab
  };
}

/** The notes beside "Prints on N pages at S%". */
export function printNotes(info) {
  const notes = [];
  if (info.fit) {
    notes.push(
      info.excel_picks
        ? 'Excel picks this tab’s scale itself (Fit To several pages across), so a column break can fall a column away from these'
        : 'Fit To: Excel scales the tab to the page',
    );
  }
  if (info.near_edge) {
    notes.push(
      'this tab only just fits its pages: another printer can measure its columns a little differently and break it elsewhere',
    );
  }
  return notes;
}
