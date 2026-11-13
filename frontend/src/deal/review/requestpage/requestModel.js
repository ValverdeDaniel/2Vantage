// The request page's pure helpers (plan.md §8.8; L24, L26, L27, L29; old 891f1b3 `RequestRail.jsx` STATUS,
// `requestFilters.js`). The server says where every item stands (`status`); these group, filter and word it. The
// statuses' words come from /api/meta/ `review.rail_statuses` (rule 1).

export const PANES = ['intake', 'census', 'questionnaire', 'documents'];

// The Show chips (L27): what each keeps, by the items' own status.
export const SHOWS = [
  { key: 'all', label: 'All' },
  { key: 'question', label: 'Client questions' },
  { key: 'answered', label: 'To review' },
  { key: 'in_cart', label: 'In the tray' },
  { key: 'missing', label: 'Missing' },
];

// A status's chip class (reviewrequest.css, the old rail's).
export const STATUS_CLASSES = {
  in_cart: 'rr-rail-chip-cart',
  question: 'rr-rail-chip-question',
  answered: 'rr-rail-chip-answered',
  asked: 'rr-rail-chip-asked',
  on_file: 'rr-rail-chip-file',
  missing: '',
};

/** The tab `?pane=` names, else the first. */
export function paneOf(params) {
  const asked = params.get('pane');
  return PANES.includes(asked) ? asked : PANES[0];
}

/** The Show chip `?show=` names, else All. */
export function showOf(params) {
  const asked = params.get('show');
  return SHOWS.some((show) => show.key === asked) ? asked : 'all';
}

/** The items a Show chip keeps. */
export function shown(items, show) {
  return show === 'all' ? items : (items || []).filter((item) => item.status === show);
}

export const REQUIRED = 'Required to market';

/**
 * The rail's sections, in the items' order: [{key, label, items, toAsk: [ref]}]; `toAsk` is what "＋ Add all" takes.
 * What the deal needs and is still missing is lifted into "Required to market" first (L29; old RequestRail `required`),
 * and not listed again below it.
 */
export function sectionsOf(items) {
  const lifted = (items || []).filter((item) => item.needed && item.status === 'missing');
  const out = lifted.length ? [{ key: REQUIRED, label: REQUIRED, items: lifted, toAsk: lifted.map((item) => item.ref) }] : [];
  const taken = new Set(lifted.map((item) => item.ref));
  (items || []).filter((item) => !taken.has(item.ref)).forEach((item) => {
    let section = out[out.length - 1];
    if (!section || section.key !== item.section) {
      section = { key: item.section, label: item.section, items: [], toAsk: [] };
      out.push(section);
    }
    section.items.push(item);
    if (item.status === 'missing') section.toAsk.push(item.ref);
  });
  return out;
}

/** "3 to ask" / "none left to ask" / "nothing missing" for a section head (old askWords). */
export function askWords(section) {
  if (section.toAsk.length) return `${section.toAsk.length} to ask`;
  return section.items.some((item) => ['asked', 'in_cart'].includes(item.status)) ? 'none left to ask' : 'nothing missing';
}

/** "Asked · Oct 20", "In the tray", … for an item's chip; '' for nothing to say. */
export function chipWords(item, labels) {
  if (item.status === 'missing') return '';
  const words = labels?.[item.status] || item.status;
  if (item.status === 'asked' && item.asked_at) {
    const date = new Date(item.asked_at);
    if (!Number.isNaN(date.getTime())) return `${words} · ${date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}`;
  }
  return words;
}

/** A census column's chips (old ColumnRow): [[words, class]]. */
export function columnChips(column) {
  const chips = [];
  if (column.in_cart) chips.push([`${column.in_cart} in the tray`, 'rr-rail-chip-cart']);
  if (column.asked) chips.push([`Asked · ${column.asked}`, 'rr-rail-chip-asked']);
  else if (column.on_link && column.blank) chips.push(['On their form', 'rr-rail-chip-asked']);
  if (column.questions) chips.push([`${column.questions} question${column.questions === 1 ? '' : 's'} open`, 'rr-rail-chip-question']);
  if (column.answered) chips.push([`${column.answered} answered`, 'rr-rail-chip-answered']);
  if (column.blank) chips.push([`${column.blank} blank`, '']);
  if (!chips.length) chips.push(['On file', 'rr-rail-chip-file']);
  return chips;
}

/** "N need you" in the header (L24): what came back and the client's questions, every tab. */
export function needYou(panes) {
  return (panes || []).reduce((sum, pane) => sum + (pane.waiting || 0), 0);
}
