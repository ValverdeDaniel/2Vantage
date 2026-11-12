// The census format lens, pure (plan.md §8.12; K79–K88; old CensusFormatLens.jsx and ExportReadiness.jsx at 891f1b3):
// the words the readiness cards, the chips and the lens show. Everything else is the server's.

const plural = (count, noun) => `${count} ${noun}${count === 1 ? '' : 's'}`;

/** A chip's short mark in the carrier's own terms. */
export function badgeOf(carrier) {
  const known = { 'Warner Pacific': 'WP', Aetna: 'AE', UnitedHealthcare: 'UHC', 'Angle Health': 'AN' };
  if (known[carrier]) return known[carrier];
  const words = (carrier || '?').split(/\s+/).filter(Boolean);
  return (words.length > 1 ? words[0][0] + words[1][0] : (words[0] || '?').slice(0, 2)).toUpperCase();
}

/** A readiness card's status (K79): ready, or how many things to fix. */
export function statusWords(format) {
  if (format.to_fix == null) return { text: 'No census yet', tone: '' };
  if (format.to_fix === 0) return { text: '✓ Ready to export', tone: 'ok' };
  return { text: `${plural(format.to_fix, 'thing')} to fix`, tone: 'gap' };
}

/** The cards Export readiness shows: the files this request sends, else every format (K79). */
export function readinessCards(formats) {
  const census = (formats || []).filter((format) => format.kind === 'census');
  const sent = census.filter((format) => format.in_packet || (format.required_by || []).length);
  return { cards: sent.length ? sent : census, sent: sent.length > 0 };
}

/** "160 rows · 24 columns · 3 we don't store · in the packet" (K80). */
export function chipSub(format) {
  const gaps = format.gaps ? ` · ${format.gaps} we don't store` : '';
  return `${format.rows} rows · ${format.columns} columns${gaps}${format.in_packet ? ' · in the packet' : ''}`;
}

/** "160 rows · room for 213" on a readiness card. */
export function rowsWords(format) {
  return `${plural(format.rows, 'row')}${format.capped ? ` · room for ${format.max_rows}` : ''}`;
}

/** The filled share's colour (K83): green at 100, amber from 90, else rose. */
export function filledClass(pct) {
  if (pct >= 100) return 'bb-green';
  if (pct >= 90) return 'bb-amber';
  return 'bb-rose';
}

/** A column's fill bar (K87): of the rows it applies to, how many hold a value. */
export function fillBar(column) {
  if (!column.expected) return null;
  const have = column.expected - column.blank;
  return {
    have,
    pct: Math.round((100 * have) / column.expected),
    short: Boolean(column.blank && column.carrier_required),
  };
}

export const FILL_WORDS = { census: 'Our census', derived: 'Worked out', gap: 'Nothing' };

/** "This format still needs Gender, ZIP for columns UnitedHealthcare requires." */
export function needsWords(detail) {
  const labels = (detail.needs || []).map((need) => need.label).join(', ');
  return labels ? labels : '';
}

/** The preview's foot: "The first 50 of 160 rows" or "All 4 rows". */
export function previewWords(preview) {
  return preview.rows.length < preview.total_rows
    ? `The first ${preview.rows.length} of ${preview.total_rows} rows`
    : `All ${preview.total_rows} rows`;
}

/** The columns we never write (K88): "52 columns (“Employee Information - Enrollment”), 41 of them their own formulas". */
export function notSentWords(notSent) {
  const columns = notSent?.columns || [];
  if (!columns.length) return '';
  const banner = notSent.unwritten_banner ? ` (“${notSent.unwritten_banner}”)` : '';
  const formulas = columns.filter((column) => column.formula).length;
  return `${plural(columns.length, 'column')}${banner}, ${formulas} of them their own formulas`;
}
