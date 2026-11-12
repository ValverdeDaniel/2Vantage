import { describe, expect, it } from 'vitest';
import { compareValues, holdOrder, nextSort, sortBy } from './sort';

const plans = [
  { id: 1, total: 17000, name: 'Cigna' },
  { id: 2, total: null, name: 'aetna' },
  { id: 3, total: 9000, name: 'UnitedHealthcare' },
  { id: 4, total: 17000, name: 'Aetna' },
];

describe('F32 sortBy', () => {
  it('sorts numbers by size, keeps ties in their order, and puts blanks last', () => {
    expect(sortBy(plans, (p) => p.total, 1).map((p) => p.id)).toEqual([3, 1, 4, 2]);
    expect(sortBy(plans, (p) => p.total, -1).map((p) => p.id)).toEqual([1, 4, 3, 2]);
  });

  it('sorts text without case', () => {
    expect(sortBy(plans, (p) => p.name, 1).map((p) => p.id)).toEqual([2, 4, 1, 3]);
    expect(compareValues('aetna', 'Aetna')).toBe(0);
    expect(compareValues(2, 10)).toBe(-1);
  });

  it('a header click sorts, and a second click flips the direction', () => {
    expect(nextSort({ key: 'proposal', dir: 1 }, 'total')).toEqual({ key: 'total', dir: 1 });
    expect(nextSort({ key: 'total', dir: 1 }, 'total')).toEqual({ key: 'total', dir: -1 });
    expect(nextSort({ key: 'total', dir: -1 }, 'total')).toEqual({ key: 'total', dir: 1 });
  });
});

describe('F33 holdOrder', () => {
  it('takes the fresh order when the sort or a filter changes', () => {
    const first = holdOrder(null, 'total:1', [3, 1, 4], new Set([1, 3, 4]));
    expect(first.ids).toEqual([3, 1, 4]);
    expect(first.held).toEqual({ key: 'total:1', ids: [3, 1, 4] });
    const resorted = holdOrder(first.held, 'total:-1', [1, 4, 3], new Set([1, 3, 4]));
    expect(resorted.ids).toEqual([1, 4, 3]);
  });

  it('holds the order while values move, and puts a new row last', () => {
    const { held } = holdOrder(null, 'total:1', [3, 1, 4], new Set([1, 3, 4]));
    // A typed rate made plan 4 the cheapest; the board keeps its rows where they were.
    expect(holdOrder(held, 'total:1', [4, 3, 1], new Set([1, 3, 4])).ids).toEqual([3, 1, 4]);
    const added = holdOrder(held, 'total:1', [5, 4, 3, 1], new Set([1, 3, 4, 5]));
    expect(added.ids).toEqual([3, 1, 4, 5]);
    expect(added.held.ids).toEqual([3, 1, 4, 5]);
  });

  it('drops rows that left the grid and keeps the same held object when nothing changed', () => {
    const { held } = holdOrder(null, 'k', [3, 1, 4], new Set([1, 3, 4]));
    expect(holdOrder(held, 'k', [3, 4], new Set([3, 4])).ids).toEqual([3, 4]);
    expect(holdOrder(held, 'k', [1, 3, 4], new Set([1, 3, 4])).held).toBe(held);
  });
});
