// The Benefits home's row logic (old homeRows.js and tableSort.js at 891f1b3; I74–I82, I86): pure, no React, pinned by
// homeRows.test.js. Every row comes from ONE feed (GET work-queue/, agenda/queue/feed.py), whose server works out each
// row's facts (`due_in`, `held`, `finished`, `client_status`, …), so the filters here are plain comparisons (ch. 12):
// the Work queue shows all of it, one row per thing to do; Prospects narrows it to Prospect clients' deals and keeps
// each client ONCE (OQ95 as reworded by OQ101 c). Vocabularies (types, due buckets, stages) come from /api/meta/.

export const ACTION_ICONS = { error: '⚠', warn: '⚠', info: '▸', done: '✓', lost: '✕' };

// The deal type's chip (old TYPE_META's badges; labels from meta `deal_types`).
export const TYPE_BADGES = { new_business: 'bb-badge-green', renewal: 'bb-badge-amber' };

export const NO_FILTERS = {
  type: 'all',
  due: 'all',
  owner: 'all',
  stage: 'all',
  category: 'all',
  selectedClient: null,
  clientQuery: '',
};

const SOLD = 'sold';
const LOST = 'lost';
const PROSPECT = 'prospect';

/** A feed row in the shape the home tables' ArchiveCell reads: the client, and its deal (I126). */
export function archiveRow(row) {
  return { id: row.client_id, name: row.client_name, deal: { id: row.deal_id } };
}

/** The stage bar's colour by its percent (old `barClass`). */
export function barClass(pct) {
  if (pct >= 90) return 'bb-bar-green';
  if (pct >= 60) return 'bb-bar-amber';
  return 'bb-bar-blue';
}

/** Does a row's `due_in` land in the bucket ({key, min, max} from meta; null is an open end)? Undated rows match All
 *  only. */
export function inDueBucket(dueIn, bucket) {
  if (!bucket || bucket.key === 'all') return true;
  if (dueIn === null || dueIn === undefined) return false;
  if (bucket.min !== null && bucket.min !== undefined && dueIn < bucket.min) return false;
  return !(bucket.max !== null && bucket.max !== undefined && dueIn > bucket.max);
}

/* Rank a client name against a typed query: 0 = the whole name starts with it, 1 = a word starts with it ("o" finds
   "Evergreen Outdoors"), 2 = a plain substring, -1 = no match. Lower ranks sort first. */
export function clientMatchRank(name, q) {
  if (!q) return 1;
  const lower = name.toLowerCase();
  if (lower.startsWith(q)) return 0;
  if (lower.split(/\s+/).some((word) => word.startsWith(q))) return 1;
  if (lower.includes(q)) return 2;
  return -1;
}

/** The search's dropdown: the names matching the typed words, best first. */
export function clientOptions(names, query) {
  const q = query.trim().toLowerCase();
  return names
    .map((name) => ({ name, rank: clientMatchRank(name, q) }))
    .filter((option) => option.rank >= 0)
    .sort((a, b) => a.rank - b.rank || a.name.localeCompare(b.name))
    .map((option) => option.name);
}

function ownerMatches(row, owner) {
  if (owner === 'all') return true;
  return owner === 'none' ? !row.owner_id : row.owner_id === Number(owner);
}

const bucketOf = (buckets, key) => (buckets || []).find((bucket) => bucket.key === key);

/* The Work queue: every row. Finished deals are hidden unless the Sold stage or a search for the client asks; lost
   deals likewise with the Lost stage, though a task on a lost deal stays ("check back in six months", I71, I80). */
export function filterQueue(rows, filters, buckets) {
  const { selectedClient, type, due, owner, stage, category } = filters;
  return rows.filter((row) => {
    const searched = selectedClient && row.client_name === selectedClient;
    if (selectedClient && !searched) return false;
    if (row.kind === 'deal' && row.finished && !row.lost && stage !== SOLD && !searched) return false;
    if (row.kind === 'deal' && row.lost && stage !== LOST && !searched) return false;
    if (type !== 'all' && row.type !== type) return false;
    if (!inDueBucket(row.due_in, bucketOf(buckets, due))) return false;
    if (!ownerMatches(row, owner)) return false;
    if (stage !== 'all' && row.stage !== stage) return false;
    return category === 'all' || row.category === category;
  });
}

export const isProspectRow = (row) => row.kind === 'deal' && row.client_status === PROSPECT;

/* Prospects, before the one-per-client collapse: Prospect clients' deals only (a sale moves a client to Clients at
   once, I122). Type and category are not read: every row here is a Prospect's deal. */
export function filterProspects(rows, filters, buckets) {
  const { selectedClient, due, owner, stage } = filters;
  return rows.filter((row) => {
    if (!isProspectRow(row)) return false;
    if (selectedClient && row.client_name !== selectedClient) return false;
    if (stage === LOST) {
      if (!row.lost) return false;
    } else {
      if (!selectedClient && (row.finished || row.lost)) return false;
      if (stage !== 'all' && row.stage !== stage) return false;
    }
    return inDueBucket(row.due_in, bucketOf(buckets, due)) && ownerMatches(row, owner);
  });
}

/* Which of a client's deals speaks for its row: an open deal before a closed one, then the soonest due (undated
   last), then the newest deal. */
function nextFirst(a, b) {
  const aClosed = a.finished || a.lost;
  const bClosed = b.finished || b.lost;
  if (aClosed !== bClosed) return aClosed ? 1 : -1;
  if (a.due !== b.due) {
    if (!a.due) return 1;
    if (!b.due) return -1;
    return a.due < b.due ? -1 : 1;
  }
  return b.deal_id - a.deal_id;
}

/** Deal rows collapsed to one per client (its next action only); `dealCount` says how many stood behind it. */
export function onePerClient(rows) {
  const groups = new Map();
  rows.forEach((row) => {
    const current = groups.get(row.client_id);
    if (!current) groups.set(row.client_id, { best: row, count: 1 });
    else {
      current.count += 1;
      if (nextFirst(row, current.best) < 0) current.best = row;
    }
  });
  return [...groups.values()].map(({ best, count }) => ({ ...best, dealCount: count }));
}

// The sortable columns' first direction (money biggest first, names A→Z, the newest reach-out first; D-159).
export const HOME_SORT_DIRS = { client: 'asc', deal: 'desc', due: 'asc', response: 'desc' };

export function homeSortValue(row, key) {
  if (key === 'client') return row.client_name;
  if (key === 'deal') return row.deal_size === null || row.deal_size === undefined ? null : Number(row.deal_size);
  if (key === 'due') return row.due;
  if (key === 'response') return row.response?.at ? Date.parse(row.response.at) : null;
  return null;
}

const isBlank = (value) => value === null || value === undefined || value === '' || Number.isNaN(value);

/* Click-to-sort (old tableSort.js): a blank value sinks to the bottom in both directions, and ties keep the order the
   rows arrived in. */
export function sortRows(rows, sort, valueOf = homeSortValue) {
  if (!sort) return rows;
  const factor = sort.dir === 'desc' ? -1 : 1;
  return rows
    .map((row, index) => ({ row, index, value: valueOf(row, sort.key) }))
    .sort((a, b) => {
      const aBlank = isBlank(a.value);
      const bBlank = isBlank(b.value);
      if (aBlank || bBlank) return aBlank === bBlank ? a.index - b.index : aBlank ? 1 : -1;
      const cmp =
        typeof a.value === 'string'
          ? a.value.localeCompare(b.value, undefined, { sensitivity: 'base' })
          : (a.value > b.value) - (a.value < b.value);
      return cmp * factor || a.index - b.index;
    })
    .map((entry) => entry.row);
}

/** The next sort after a click on `key`: the same column flips, another starts in its own direction. */
export function nextSort(sort, key, dirs = HOME_SORT_DIRS) {
  if (sort && sort.key === key) return { key, dir: sort.dir === 'asc' ? 'desc' : 'asc' };
  return { key, dir: dirs[key] || 'asc' };
}

// ---- Client responses (D-159) ---------------------------------------------------------------------------------------

export const waitingOnUs = (row) => row.response?.state === 'waiting';

/** When the client last reached out, in the old column's words (old `agoWords`): "3h ago", "2d ago", else the date. */
export function agoWords(iso, now = new Date()) {
  if (!iso) return '';
  const seconds = Math.round((now.getTime() - new Date(iso).getTime()) / 1000);
  if (seconds < 60) return 'just now';
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  return days < 31 ? `${days}d ago` : new Date(iso).toLocaleDateString('en-US');
}

const RESPONSE_RANK = { waiting: 0, answering: 1, answered: 2 };

/** "Responses first": waiting on us, then still answering, then answered, then the rest, each group in table order. */
export function responsesFirst(rows) {
  const rank = (row) => RESPONSE_RANK[row.response?.state] ?? 3;
  return rows
    .map((row, index) => ({ row, index, rank: rank(row) }))
    .sort((a, b) => a.rank - b.rank || a.index - b.index)
    .map((entry) => entry.row);
}

/** The card's and the toggle's count over deal rows: the deals waiting on us, and their questions and answers. */
export function responseTotals(rows) {
  const waiting = rows.filter((row) => row.kind === 'deal' && waitingOnUs(row));
  return {
    deals: waiting.length,
    questions: waiting.reduce((n, row) => n + (row.response.questions || 0), 0),
    answers: waiting.reduce((n, row) => n + (row.response.answers || 0), 0),
  };
}

// ---- The Work queue's two modes (I74, I75) --------------------------------------------------------------------------

/** Held back by someone (Later) until a day after the agency's `today` (both ISO days). */
export function isHeld(row, today) {
  return Boolean(row.held && row.held > today);
}

// One of a deal's open steps as a queue row: the deal's facts, so filters and sorts work, with the step's words.
function stepRow(deal, step) {
  return {
    ...deal,
    kind: 'step',
    id: `${deal.id}:${step.id}`,
    key: step.key,
    label: step.label,
    link: step.link,
    severity: step.severity,
    held: step.later_until || null,
    due: step.due || deal.due,
    due_in: step.due ? step.due_in : deal.due_in,
    steps: undefined,
  };
}

/* The rows the Work queue lists: each deal's next step, or with `steps` every open step of every deal (a deal with
   none, waiting or finished, then has no row). Held rows stay out unless `showLater`. */
export function queueView(rows, { steps = false, showLater = false, today }) {
  const out = [];
  rows.forEach((row) => {
    if (steps && row.kind === 'deal') {
      (row.steps || []).forEach((step) => out.push(stepRow(row, step)));
      return;
    }
    out.push(row);
  });
  return showLater ? out : out.filter((row) => !isHeld(row, today));
}

/** The Overdue and Due this week cards (I82): the mode's rows, never held ones or finished or lost deals', each by its
 *  own due day; they ignore the filters, as the old cards did. */
export function dueCards(rows, buckets) {
  const open = rows.filter((row) => !row.finished && !row.lost);
  return {
    overdue: open.filter((row) => inDueBucket(row.due_in, bucketOf(buckets, 'overdue'))).length,
    week: open.filter((row) => inDueBucket(row.due_in, bucketOf(buckets, 'week'))).length,
  };
}
