import { describe, expect, it } from 'vitest';
import {
  clientOptions,
  dueCards,
  filterProspects,
  filterQueue,
  inDueBucket,
  isHeld,
  NO_FILTERS,
  nextSort,
  onePerClient,
  queueView,
  responsesFirst,
  responseTotals,
  sortRows,
} from './homeRows';

// The due buckets as /api/meta/ `agenda.queue.due` serves them (agenda/catalogue.py).
const BUCKETS = [
  { key: 'overdue', min: null, max: -1 },
  { key: 'week', min: 0, max: 7 },
  { key: '30', min: 0, max: 30 },
  { key: '90', min: 0, max: 90 },
  { key: 'all', min: null, max: null },
];

let next = 1;
function deal(more = {}) {
  const id = next++;
  return {
    kind: 'deal',
    id: `deal:${id}`,
    deal_id: id,
    client_id: id,
    client_name: `Client ${id}`,
    client_status: 'prospect',
    type: 'new_business',
    stage: 'intake',
    category: 'pipeline',
    due: '2026-12-01',
    due_in: 19,
    owner_id: 7,
    held: null,
    finished: false,
    lost: false,
    steps: [],
    ...more,
  };
}

const task = (on, more = {}) => ({ ...on, kind: 'task', id: `task:${on.deal_id}`, category: 'task', ...more });

describe('the Work queue filters (I78, I80)', () => {
  it('I78 due buckets are plain comparisons on due_in, and an undated row matches All only', () => {
    expect(inDueBucket(-1, BUCKETS[0])).toBe(true);
    expect(inDueBucket(0, BUCKETS[0])).toBe(false);
    expect([0, 7, 8].map((n) => inDueBucket(n, BUCKETS[1]))).toEqual([true, true, false]);
    expect(inDueBucket(null, BUCKETS[1])).toBe(false);
    expect(inDueBucket(null, BUCKETS[4])).toBe(true);
  });

  it('I80 hides finished and lost deals unless their stage or a client search asks, but keeps a lost deals task', () => {
    const sold = deal({ stage: 'sold', finished: true });
    const lost = deal({ stage: 'lost', finished: true, lost: true });
    const open = deal();
    const rows = [sold, lost, open, task(lost, { lost: true })];
    expect(filterQueue(rows, NO_FILTERS, BUCKETS).map((row) => row.id)).toEqual([open.id, `task:${lost.deal_id}`]);
    expect(filterQueue(rows, { ...NO_FILTERS, stage: 'sold' }, BUCKETS)).toEqual([sold]);
    expect(filterQueue(rows, { ...NO_FILTERS, stage: 'lost' }, BUCKETS).map((row) => row.kind)).toEqual([
      'deal',
      'task',
    ]);
    const searched = { ...NO_FILTERS, selectedClient: lost.client_name };
    expect(filterQueue(rows, searched, BUCKETS)).toHaveLength(2);
  });

  it('I78 type, owner (Unassigned too) and category narrow the rows', () => {
    const renewal = deal({ type: 'renewal', owner_id: null });
    const rows = [deal(), renewal, task(renewal)];
    expect(filterQueue(rows, { ...NO_FILTERS, type: 'renewal' }, BUCKETS)).toHaveLength(2);
    expect(filterQueue(rows, { ...NO_FILTERS, owner: 'none' }, BUCKETS)).toHaveLength(2);
    expect(filterQueue(rows, { ...NO_FILTERS, category: 'task' }, BUCKETS).map((row) => row.kind)).toEqual(['task']);
  });

  it('A11 the client search ranks a name start, then a word start, then any match', () => {
    const names = ['Blue Harbor', 'Evergreen Outdoors', 'Oakline', 'Coastal Co'];
    expect(clientOptions(names, 'o')).toEqual(['Oakline', 'Evergreen Outdoors', 'Blue Harbor', 'Coastal Co']);
  });
});

describe('Prospects on the work feed (I86, I122, OQ95)', () => {
  it('I122 lists only Prospect clients, so a sold client is gone at once', () => {
    const prospect = deal();
    const won = deal({ client_status: 'new_client', stage: 'sold' });
    expect(filterProspects([prospect, won, task(prospect)], NO_FILTERS, BUCKETS)).toEqual([prospect]);
  });

  it('I86 keeps each client once, an open deal before a closed one, then the soonest due', () => {
    const later = deal({ due: '2027-03-01' });
    const sooner = { ...deal({ due: '2027-01-01' }), client_id: later.client_id };
    const closed = { ...deal({ due: '2026-11-01', lost: true }), client_id: later.client_id };
    const [row] = onePerClient([later, closed, sooner]);
    expect(row.id).toBe(sooner.id);
    expect(row.dealCount).toBe(3);
  });
});

describe('sorting and Responses first (I79, I81)', () => {
  it('I81 a blank sinks in both directions and ties keep their order', () => {
    const rows = [deal({ deal_size: null }), deal({ deal_size: '50000.00' }), deal({ deal_size: '250000.00' })];
    const down = sortRows(rows, { key: 'deal', dir: 'desc' }).map((row) => row.deal_size);
    expect(down).toEqual(['250000.00', '50000.00', null]);
    const up = sortRows(rows, { key: 'deal', dir: 'asc' }).map((row) => row.deal_size);
    expect(up).toEqual(['50000.00', '250000.00', null]);
    expect(nextSort({ key: 'deal', dir: 'desc' }, 'deal')).toEqual({ key: 'deal', dir: 'asc' });
    expect(nextSort(null, 'client')).toEqual({ key: 'client', dir: 'asc' });
  });

  it('I79 lifts the deals waiting on us, then still answering, then answered', () => {
    const quiet = deal();
    const answered = deal({ response: { state: 'answered' } });
    const waiting = deal({ response: { state: 'waiting', questions: 2, answers: 1 } });
    const typing = deal({ response: { state: 'answering' } });
    const order = responsesFirst([quiet, answered, waiting, typing]);
    expect(order).toEqual([waiting, typing, answered, quiet]);
    expect(responseTotals(order)).toEqual({ deals: 1, questions: 2, answers: 1 });
  });
});

describe('the two modes and the due cards (I74, I75, I82)', () => {
  const today = '2026-11-12';
  const steps = [
    { id: 'step:a', key: 'a', label: 'A', link: '/deals/1/intake', severity: 'info', due: null, due_in: null },
    { id: 'step:b', key: 'b', label: 'B', link: '/deals/1/census', later_until: '2026-11-20', due: null },
  ];

  it('I74 All open steps lists every open step of each deal, under ids that never collide', () => {
    const one = deal({ steps });
    const two = deal({ steps });
    const shown = queueView([one, two], { steps: true, showLater: true, today });
    expect(shown.map((row) => row.kind)).toEqual(['step', 'step', 'step', 'step']);
    expect(new Set(shown.map((row) => row.id)).size).toBe(4);
  });

  it('I75 a held row waits for Show held until later', () => {
    const held = deal({ held: '2026-11-15' });
    const back = deal({ held: '2026-11-12' });
    expect(isHeld(held, today)).toBe(true);
    expect(queueView([held, back], { today }).map((row) => row.id)).toEqual([back.id]);
    expect(queueView([held, back], { showLater: true, today })).toHaveLength(2);
  });

  it('I82 the cards count each row by its own due day, never a finished or lost deal', () => {
    const rows = [
      deal({ due_in: -2 }),
      deal({ due_in: 3 }),
      deal({ due_in: -5, finished: true }),
      deal({ due_in: 40 }),
    ];
    expect(dueCards(rows, BUCKETS)).toEqual({ overdue: 1, week: 1 });
  });
});
