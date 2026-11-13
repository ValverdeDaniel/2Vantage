// The home page's URL (plan.md §8.3): which view, the search, the Clients chip, the sort and the page all live in the
// query string, so Back restores them. A pure module: HomePage reads it, homeParams.test.js pins it.
//   (bare /)   Prospects, the landing view (OQ95)      ?view=book   Clients (CL10)    ?view=queue   Work queue (61)
//   ?q=        Clients' server-side search             ?status=     a Clients chip: one client status key
//   ?ordering=name   Client A→Z (default: last updated) ?page=       25 rows a page
//   &steps=all       the Work queue's All open steps (I74), written only on a click, as the old one was
// Prospects and the Work queue filter the one work feed in the browser, their filters in the page's state (the old
// home's), so only the view and the queue's mode are in the URL there.

export const PAGE_SIZE = 25;
export const BY_NAME = 'name';

// The view pill, in the old order (CL10): the old New clients view is Prospects (OQ95 as reworded by OQ101 c).
export const VIEWS = [
  { key: 'prospects', label: 'Prospects' },
  { key: 'book', label: 'Clients' },
  { key: 'queue', label: 'Work queue' },
];
const KNOWN = new Set(['book', 'queue']);

/** {view, q, status, ordering, page, steps} from the URL; anything unknown reads as its default. */
export function readHome(params) {
  const asked = params.get('view');
  const view = KNOWN.has(asked) ? asked : 'prospects';
  const page = Number.parseInt(params.get('page'), 10);
  return {
    view,
    q: params.get('q') || '',
    status: view === 'book' ? params.get('status') || '' : '',
    ordering: params.get('ordering') === BY_NAME ? BY_NAME : '',
    page: page > 1 ? page : 1,
    steps: view === 'queue' && params.get('steps') === 'all',
  };
}

/** The URL for another view: the old pill writes only `view` (none for the landing view) and drops the rest. */
export function viewParams(view) {
  return new URLSearchParams(KNOWN.has(view) ? { view } : {});
}

/** The Work queue's mode in the URL: `steps=all` for All open steps, nothing for Next step (I74). */
export function stepsParams(params, on) {
  const next = new URLSearchParams(params);
  if (on) next.set('steps', 'all');
  else next.delete('steps');
  return next;
}

/** The URL after `changes` ({q, status, ordering, page}): defaults leave the URL, and any change but the page
 *  goes back to page 1. */
export function changeHome(params, changes) {
  const next = new URLSearchParams(params);
  for (const [key, value] of Object.entries(changes)) {
    const isDefault = value === '' || value == null || (key === 'page' && Number(value) <= 1);
    if (isDefault) next.delete(key);
    else next.set(key, String(value));
  }
  if (!('page' in changes)) next.delete('page');
  return next;
}

/** GET clients/'s query for the view (CL11, CL12): Prospects asks for `prospect`; Clients for its chip's status, or
 *  every client status as the comma list. `statuses` are the Clients view's keys, from /api/meta/. */
export function listQuery(state, { prospect, statuses }) {
  let relationship = prospect;
  if (state.view === 'book') {
    relationship = statuses.includes(state.status) ? state.status : statuses.join(',');
  }
  return {
    q: state.q.trim(),
    relationship,
    ordering: state.ordering,
    page: state.page > 1 ? state.page : '',
  };
}

/** The Clients chips (CL12): All, then one per client status from /api/meta/, named in the plural. */
export function statusChips(statuses) {
  return [{ key: '', label: 'All' }, ...statuses.map((status) => ({ key: status.key, label: `${status.label}s` }))];
}

/** "Page 2 of 3", or null when everything fits on one page. */
export function pageWords(page, count, size = PAGE_SIZE) {
  const pages = Math.max(1, Math.ceil(count / size));
  return pages > 1 ? { page: Math.min(page, pages), pages } : null;
}
