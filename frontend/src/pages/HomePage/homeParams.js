// The home page's URL (plan.md §8.3): which view, the search, the Clients chip, the sort and the page all live in the
// query string, so Back restores them. A pure module: HomePage reads it, homeParams.test.js pins it.
//   (bare /)   Prospects, the landing view (OQ95)      ?view=book   Clients (CL10)
//   ?q=        the server-side search                  ?status=     a Clients chip: one client status key
//   ?ordering=name   Client A→Z (default: last updated) ?page=       25 rows a page

export const PAGE_SIZE = 25;
export const BY_NAME = 'name';

// The view pill, in the old order with the old Work queue left out until slice 61 (CL10).
export const VIEWS = [
  { key: 'prospects', label: 'Prospects' },
  { key: 'book', label: 'Clients' },
];

/** {view, q, status, ordering, page} from the URL; anything unknown reads as its default. */
export function readHome(params) {
  const view = params.get('view') === 'book' ? 'book' : 'prospects';
  const page = Number.parseInt(params.get('page'), 10);
  return {
    view,
    q: params.get('q') || '',
    status: view === 'book' ? params.get('status') || '' : '',
    ordering: params.get('ordering') === BY_NAME ? BY_NAME : '',
    page: page > 1 ? page : 1,
  };
}

/** The URL for another view: the old pill writes only `view` (none for the landing view) and drops the rest. */
export function viewParams(view) {
  return new URLSearchParams(view === 'book' ? { view } : {});
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
