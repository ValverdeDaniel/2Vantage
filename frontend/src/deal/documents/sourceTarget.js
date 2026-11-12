/*
 * Where a value opens in its file (plan.md §10.7; E18, E23, E24, D-122): the old shared/sourceTarget.js. The page the
 * locator found it on beats the page the read recorded; a figure printed once there may be boxed even when short
 * (`exact`); a sheet value opens on its own cell (the locator's, else the read's `cell`, "Medical!C7"); a figure the
 * reader worked out is searched as what is printed (`printed`). Pure.
 */

const LOCATED = ['found', 'derived', 'weak'];

/** The reader's line without the `· printed "…"` note the normalizer appends: the file prints the line only. */
export function readerLine(line) {
  const text = String(line || '').trim();
  if (text.startsWith('printed "')) return '';
  return text.replace(/\s*·\s*printed ".*$/s, '').trim();
}

/**
 * The viewer's `find` for one value: {page, cell, value, snippet, hint, exact}. `source` is the value's source entry
 * ({page, cell, line, loc}); `pageParam` a page the link names (`?page=`), which wins over both.
 */
export function viewerFind(source, value, hint = '', pageParam = null) {
  const loc = source?.loc || null;
  const located = Boolean(loc) && LOCATED.includes(loc.state);
  const locatedCell = located && loc.cell ? `${loc.sheet ? `${loc.sheet}!` : ''}${loc.cell}` : '';
  return {
    page: Number(pageParam) || (located && loc.page) || source?.page || null,
    cell: locatedCell || source?.cell || '',
    value: (located && loc.printed) || (value == null ? '' : String(value)),
    snippet: readerLine(source?.line),
    hint: hint || '',
    exact: Boolean(located && loc.page && loc.hits === 1),
  };
}

/** The file a value opens: the locator's file when it found the value elsewhere, else the source's `doc`. */
export function sourceDocument(source) {
  return source?.loc?.doc || source?.doc || null;
}
