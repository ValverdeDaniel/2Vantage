// The review queue's words and picks (plan.md §8.8; L11, L15, L16, L20; old 891f1b3 `DealReviewTab.jsx`
// `sectionsOf`, `CensusClientReview.jsx`, `ReadyWhy.jsx`). Pure. Labels of changes, phases and sections come from
// /api/meta/ `review` (rule 1); the server says each item's change, phase and why it is ready.

/** The queue's section chips, in the old order, with what each holds to review: [{key, label, count, questions}]. */
export function sectionsOf(meta, board) {
  return (meta?.queue_sections || []).map(({ key, label }) => {
    const found = board?.sections?.[key] || {};
    return { key, label, count: (found.to_review || 0) + (found.questions || 0), questions: found.questions || 0 };
  });
}

/** The section `?section=` names, else the first with something in it, else the first. */
export function pickedSection(sections, asked) {
  return (
    sections.find((section) => section.key === asked) ||
    sections.find((section) => section.count > 0) ||
    sections[0] ||
    null
  );
}

const plural = (n, one) => `${n} ${one}${n === 1 ? '' : 's'}`;

/** Why an answer is ready, or that it is not yet (old ReadyWhy): "Submitted", "Not submitted · idle 2 days". */
export function readyWords(item) {
  if (item.ready_why === 'submitted') return 'Submitted';
  if (item.ready_why === 'idle') return `Not submitted · idle ${plural(item.idle_days || 1, 'day')}`;
  return 'Still typing';
}

function shown(value) {
  if (Array.isArray(value)) return value.length ? value.join('; ') : '';
  return value ?? '';
}

function short(text) {
  return text.length > 60 ? `${text.slice(0, 57)}…` : text;
}

/** A row's title and sub-line (old renderSummary): "Avery One · ZIP", "33602 → 33606", "New person · Rowan Synthetic". */
export function summaryOf(item) {
  if (item.kind === 'person') {
    return { title: `${item.person} · New person`, sub: `New person · ${item.theirs || 'no name'}` };
  }
  const title = item.person ? `${item.person} · ${item.label}` : item.label;
  const sub = `${short(shown(item.ours)) || 'blank'} → ${short(shown(item.theirs)) || 'blank'}`;
  return { title, sub, flag: item.blocks?.length ? `blocks ${item.blocks.join(', ')}` : '' };
}

/** "Avery One" from a census ref's item, the member id and column a correction writes. */
export function cellOf(ref) {
  const [surface, first, second] = String(ref).split(':');
  if (surface === 'census') return { surface, memberId: Number(first), column: second };
  return { surface, key: ref.slice('intake:'.length) };
}

// What a decided row says (old DECIDED).
export const DECIDED = {
  approved: { label: 'Approved', icon: '✓' },
  corrected: { label: 'Corrected', icon: '✎' },
  kept: { label: 'Kept ours', icon: '↺' },
  undone: { label: 'Approval taken back — waiting again', icon: '↶', tone: 'back' },
  sentback: { label: 'Sent back — in the request tray, it goes when you send it', icon: '↩', tone: 'back' },
};

/** "2 answers approved" for a toast. */
export function approvedWords(n) {
  return `${plural(n, 'answer')} from the client approved`;
}

/**
 * The queue's rows after a read: the fresh items, with the ones decided this visit (`decided[id]` keeps the row as
 * `item` and where it stood as `index`) put back where they stood when they belong to the phase and group shown, so "N of
 * M reviewed" counts them and their marks stay (old: the queue kept its rows until the page was read again).
 */
export function keepDecided(fresh, decided, { phase, group = '' }) {
  const out = [...fresh];
  const present = new Set(fresh.map((item) => item.id));
  Object.values(decided)
    .filter(({ item }) => item && !present.has(item.id) && item.phase === phase && (!group || item.group === group))
    .sort((a, b) => a.index - b.index)
    .forEach(({ item, index }) => out.splice(Math.min(index, out.length), 0, item));
  return out;
}

/** The row to open: the one asked for while it is listed, else the first nobody decided, else none. */
export function focusOf(items, focusId, decided) {
  if (items.some((item) => item.id === focusId)) return focusId;
  return items.find((item) => !decided[item.id])?.id ?? null;
}
