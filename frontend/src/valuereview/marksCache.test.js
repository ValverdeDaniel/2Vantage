import { describe, expect, it } from 'vitest';
import { cellCounts, flaggedKeys, isPotential, patchComparison, planCounts } from './marksCache';

const plan = (id, cells, facts = { flags: 0, incomplete: false }) => ({ id, cells, facts, values: {} });

describe('review marks on the compact comparison (F63–F65, E53)', () => {
  it('F63 counts open warnings and flags from the server cells, never deciding them', () => {
    const cells = [{ s: 'to_check' }, { s: 'to_check', m: 'check' }, { m: 'approved' }, { o: 'ai' }, undefined];
    expect(cellCounts(cells)).toEqual({ open: 2, check: 1, unflagged: 1 });
    expect(planCounts(plan(1, { a: { s: 'to_check' }, b: { s: 'missing' } }))).toEqual({ open: 1, check: 0, unflagged: 1 });
  });

  it('F63 lists a quote’s values to review in the board’s field order', () => {
    const quote = plan(1, { rate_fam: { s: 'to_check' }, deductible_single: { s: 'to_check', m: 'check' }, rate_ee: {} });
    expect(flaggedKeys(quote, ['deductible_single', 'rate_ee', 'rate_fam'])).toEqual(['deductible_single', 'rate_fam']);
  });

  it('E53 lays a review answer over the cached cells and counts, leaving other plans untouched', () => {
    const other = plan(2, { rate_ee: { s: 'to_check' } }, { flags: 1, incomplete: false });
    const data = {
      groups: [],
      plans: [plan(1, { rate_ee: { s: 'to_check', o: 'ai', d: 0 }, rate_fam: { s: 'to_check', m: 'check' } }, { flags: 2 }), other],
    };
    const answer = {
      values: [
        { plan_id: 1, key: 'rate_ee', cell: { m: 'approved' } },
        { plan_id: 1, key: 'rate_fam', cell: { s: 'to_check' } },
      ],
      plans: [{ id: 1, flags: 1, incomplete: true }],
    };
    const next = patchComparison(data, answer);
    expect(next.plans[0].cells.rate_ee).toEqual({ o: 'ai', d: 0, m: 'approved' });
    expect(next.plans[0].cells.rate_fam).toEqual({ s: 'to_check' });
    expect(next.plans[0].facts).toEqual({ flags: 1, incomplete: true });
    expect(next.plans[1]).toBe(other);
  });

  it('E53 returns the same data when the answer changed nothing', () => {
    const data = { groups: [], plans: [plan(1, {})] };
    expect(patchComparison(data, { values: [], plans: [] })).toBe(data);
  });

  it('E50 a potential error is an open warning or a value the locator could not find, as the server flags it', () => {
    expect(isPotential({ s: 'to_check' })).toBe(true);
    expect(isPotential({ p: 1, d: 0 })).toBe(true);
    expect(isPotential({ s: 'missing' })).toBe(false);
    expect(isPotential(undefined)).toBe(false);
    const data = { groups: [], plans: [plan(1, { rate_ee: { p: 1, d: 0 } })] };
    const approved = patchComparison(data, { values: [{ plan_id: 1, key: 'rate_ee', cell: { m: 'approved' } }] });
    expect(approved.plans[0].cells.rate_ee).toEqual({ d: 0, m: 'approved' });
  });
});
