import { describe, expect, it } from 'vitest';
import { arrowsFor, canMove, drawnOrder, lineOrder, rootOf } from './boardOrder';

// A line as the comparison sends it, in the server's order: current plans first, then quotes grouped by base_ids.
const plan = (id, role, extra = {}) => ({ id, role, carrier: 'X', name: `P${id}`, base_ids: [], ...extra });
const medical = [
  plan(1, 'current'),
  plan(2, 'current'),
  plan(3, 'renewal', { base_ids: [1] }),
  plan(4, 'alternate', { base_ids: [1] }),
  plan(5, 'alternate', { base_ids: [1], derived_from: 4, derived: { kind: 'concession' } }),
  plan(6, 'alternate', { base_ids: [2] }),
  plan(7, 'alternate', { base_ids: [] }),
  plan(8, 'alternate', { base_ids: [1], derived_from: 4, derived: { kind: 'duplicate' } }),
];

describe('F120 the order drawn', () => {
  it('heads each current plan with its quotes in the client order when the line has several', () => {
    const order = lineOrder(medical);
    const quotes = medical.filter((p) => p.role !== 'current');
    expect(drawnOrder(order, quotes, true).map((p) => p.id)).toEqual([1, 3, 4, 5, 8, 2, 6, 7]);
  });

  it('pins the current plans first under a column sort', () => {
    const order = lineOrder(medical);
    const quotes = [medical[6], medical[3]];
    expect(drawnOrder(order, quotes, false).map((p) => p.id)).toEqual([1, 2, 7, 4]);
  });

  it('a priced version rides with its quote; a duplicate is its own quote', () => {
    const byId = new Map(medical.map((p) => [p.id, p]));
    expect(rootOf(medical[4], byId).id).toBe(4);
    expect(rootOf(medical[7], byId).id).toBe(8);
  });
});

describe('F43 F44 the arrows', () => {
  it('a quote passes only the plans of its group on screen, moving with its priced versions', () => {
    const order = lineOrder(medical);
    const shown = [1, 3, 4, 5, 8, 2, 6, 7];
    expect(arrowsFor(medical[2], shown, order)).toEqual({ among: [3, 4, 5, 8], first: true, last: false });
    expect(arrowsFor(medical[4], shown, order)).toMatchObject({ first: false, last: false });
    expect(arrowsFor(medical[7], shown, order)).toMatchObject({ first: false, last: true });
    expect(arrowsFor(medical[6], shown, order)).toEqual({ among: [7], first: true, last: true });
  });

  it('current plans move among the current plans, and only beside another', () => {
    const order = lineOrder(medical);
    expect(arrowsFor(medical[1], [1, 2, 3], order)).toEqual({ among: [1, 2], first: false, last: true });
    expect(canMove(medical[0], order)).toBe(true);
    expect(canMove(plan(9, 'current'), lineOrder([plan(9, 'current'), plan(10, 'alternate')]))).toBe(false);
  });

  it('a priced version of a current plan takes no arrow', () => {
    const line = [plan(1, 'current'), plan(2, 'alternate', { base_ids: [1], derived_from: 1, derived: { kind: 'holiday' } })];
    expect(canMove(line[1], lineOrder(line))).toBe(false);
  });

  it('OQ13 the up, down, left and right arrows move a stop-loss plan like any line', () => {
    const stopLoss = [
      plan(21, 'current', { line: 'stop_loss' }),
      plan(22, 'alternate', { line: 'stop_loss', base_ids: [21] }),
      plan(23, 'alternate', { line: 'stop_loss', base_ids: [21] }),
      plan(24, 'alternate', { line: 'stop_loss', base_ids: [21] }),
    ];
    const order = lineOrder(stopLoss);
    expect(canMove(stopLoss[2], order)).toBe(true);
    expect(arrowsFor(stopLoss[2], [21, 22, 23, 24], order)).toEqual({ among: [22, 23, 24], first: false, last: false });
    expect(arrowsFor(stopLoss[1], [21, 22, 23, 24], order).first).toBe(true);
    expect(arrowsFor(stopLoss[3], [21, 22, 23, 24], order).last).toBe(true);
  });
});
