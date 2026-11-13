import { describe, expect, it } from 'vitest';
import { doneRows, doneWords, panelSub, panelTitle, pickLabel, taskTarget } from './agendaView';

const META = { stages: [{ key: 'intake', label: 'Intake' }, { key: 'sold', label: 'Sold' }] };
const deal = (id, extra = {}) => ({ id, stage: 'sold', effective_date: '2027-01-01', link: `/deals/${id}/agenda`, ...extra });

describe('the client Agenda (CL24)', () => {
  it('titles each deal panel in the old words, with its next step', () => {
    expect(panelTitle(deal(7), META)).toBe('Deal renewing 01/01/2027 · Sold');
    expect(panelTitle(deal(7, { effective_date: null, stage: 'intake' }), META)).toBe('Deal · Intake');
    expect(panelSub({ next_step: { label: 'Sold' } })).toBe(
      'What the deal needs now, and what it is waiting on. Next: Sold.',
    );
    expect(panelSub({ next_step: null })).toBe('What the deal needs now, and what it is waiting on.');
    expect(pickLabel(deal(7), META)).toBe('On the deal renewing 01/01/2027 (Sold)');
  });

  it('adds a task on the picked deal, else on the first; none without a deal', () => {
    const panels = [{ deal: deal(7) }, { deal: deal(9) }];
    expect(taskTarget(panels, '9')).toBe(9);
    expect(taskTarget(panels, '')).toBe(7);
    expect(taskTarget(panels, '12')).toBe(7);
    expect(taskTarget([], '')).toBeNull();
  });

  it('lists the ticked tasks and nudges per deal under Done, offering only ↺', () => {
    const rows = [
      { id: 'task:1', kind: 'task', section: 'done', can: { reopen: true, edit: true, delete: true } },
      { id: 'step:mark_sold', kind: 'step', section: 'done', can: {} },
      { id: 'task:2', kind: 'task', section: 'up_next', can: { tick: true } },
    ];
    const found = doneRows([{ deal: deal(7), rows }, { deal: deal(9), rows: [] }]);
    expect(found).toEqual([{ deal: deal(7), rows: [{ ...rows[0], can: { reopen: true } }] }]);
    expect(doneWords(1)).toBe('1 task done.');
    expect(doneWords(0)).toBe('0 tasks done.');
  });
});
