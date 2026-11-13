import { describe, expect, it } from 'vitest';
import { actionsOf, dayLabel, detailOf, isoIn, laterPicks, sectionsOf } from './rowView';

const META = {
  agenda: {
    sections: [
      { key: 'up_next', title: 'Up next', sub: 'Ours to do now.', empty: 'Nothing to do right now.' },
      { key: 'waiting', title: 'Waiting on', sub: '', empty: 'Not waiting on anyone.' },
      { key: 'done', title: 'Done', sub: '', empty: '' },
    ],
    owner_words: { client: 'the client', carrier: 'the carrier', us: 'us' },
    later_picks: [
      { days: 1, label: 'Tomorrow' },
      { days: 3, label: 'In 3 days' },
      { days: 7, label: 'Next week' },
    ],
  },
};

describe('days from the agency’s today (I14, I15; I.5 bug 1)', () => {
  it('I15 counts calendar days from the payload’s today, across a month end', () => {
    expect(isoIn('2026-11-29', 3)).toBe('2026-12-02');
    expect(laterPicks(META, '2026-11-12').map((pick) => pick.until)).toEqual(['2026-11-13', '2026-11-15', '2026-11-19']);
  });

  it('I15 hides a pick past the row’s later_max (a nudge’s link runs out)', () => {
    expect(laterPicks(META, '2026-11-12', '2026-11-15').map((pick) => pick.label)).toEqual(['Tomorrow', 'In 3 days']);
  });

  it('I14 prints the old row date', () => {
    expect(dayLabel('2026-11-20')).toBe('Nov 20, 2026');
  });
});

describe('rows (I4, I11, I20)', () => {
  it('I4 groups rows by the server’s section, in meta’s order', () => {
    const rows = [
      { id: 'step:a', section: 'waiting' },
      { id: 'task:1', section: 'up_next' },
    ];
    expect(sectionsOf({ rows }, META).map((s) => [s.key, s.rows.map((r) => r.id)])).toEqual([
      ['up_next', ['task:1']],
      ['waiting', ['step:a']],
      ['done', []],
    ]);
  });

  it('I11 says who a waiting step waits on, when a held one comes back, and who ticked a task', () => {
    expect(detailOf({ kind: 'step', state: 'waiting', owner: 'client' }, META)).toBe('Waiting on the client');
    const held = { kind: 'step', state: 'open', later_until: '2026-11-20', later: { by: 'Dana', note: 'On holiday' } };
    expect(detailOf(held, META)).toBe('Back Nov 20, 2026 · Dana — On holiday');
    expect(detailOf({ kind: 'step', state: 'open', done_anyway: { by: 'Dana' } }, META)).toBe('Marked done by Dana');
    const task = { kind: 'task', done: true, done_by: 'Dana', note: 'Sent by email' };
    expect(detailOf(task, META)).toBe('Done by Dana — Sent by email');
    expect(detailOf({ kind: 'task', assigned_to: { name: 'Ada' } }, META)).toBe('For Ada');
  });

  it('I20 offers only the buttons the server allows: a follow-up is logged, never done anyway', () => {
    const followUp = { kind: 'step', can: { later: true, follow_up: true, done_anyway: false } };
    expect(actionsOf(followUp).map((a) => a.label)).toEqual(['Later', 'Log follow-up']);
    const plain = { kind: 'step', can: { later: true, done_anyway: true } };
    expect(actionsOf(plain).map((a) => a.label)).toEqual(['Later', 'Done anyway']);
    expect(actionsOf({ kind: 'step', can: { bring_back: true } }).map((a) => a.label)).toEqual(['Bring back']);
    const task = { kind: 'task', can: { tick: true, later: true, edit: true, delete: false } };
    expect(actionsOf(task).map((a) => a.label)).toEqual(['Later', 'Edit', '✓']);
    expect(actionsOf({ kind: 'nudge', can: { tick: false, later: false } })).toEqual([]);
  });

  it('I37 gives an open nudge Later and ✓, as the old task row did, and never Edit or Delete', () => {
    const nudge = { kind: 'nudge', can: { tick: true, later: true } };
    expect(actionsOf(nudge).map((a) => [a.key, a.label])).toEqual([
      ['later', 'Later'],
      ['tick', '✓'],
    ]);
    expect(actionsOf({ kind: 'nudge', can: { tick: true, later: false } }).map((a) => a.key)).toEqual(['tick']);
  });
});
