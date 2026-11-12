import { describe, expect, it } from 'vitest';
import { FIRST_DRAW, WINDOW_ROWS_OVER, colsInView, frame, nextRange, rowsInView } from './windowFrame';
import { MAX_PLAN_PX, MIN_ROW_PX, fitWidth, readSizes, storeKey, writeSizes } from './gridSizes';

describe('F40 windowed rows', () => {
  it('draws every row while off, and a first slice with pads while on', () => {
    expect(frame({ count: 120, on: false })).toMatchObject({ on: false, first: 0, last: 119, before: 0, after: 0 });
    const on = frame({ count: 400, on: true, range: null });
    expect(on).toMatchObject({ on: true, first: 0, last: FIRST_DRAW.rows });
    expect(on.after).toBe((400 - 1 - FIRST_DRAW.rows) * 40);
    expect(WINDOW_ROWS_OVER).toBe(150);
  });

  it('keeps the open editor drawn, and sizes pads from the measured row height', () => {
    const drawn = frame({ count: 400, on: true, range: { first: 100, last: 140, n: 400, px: 50 }, pin: 10 });
    expect(drawn).toMatchObject({ first: 10, last: 140, before: 500, after: (400 - 1 - 140) * 50 });
  });

  it('redraws only near an edge of what is drawn', () => {
    const now = { first: 80, last: 160, n: 400, px: 40 };
    expect(nextRange(now, [100, 140], 400, 40, 20)).toBe(now);
    expect(nextRange(now, [150, 190], 400, 40, 20)).toEqual({ first: 130, last: 210, n: 400, px: 40 });
    expect(rowsInView(-4000, 900, 40, 400)).toEqual([100, 123]);
    expect(colsInView(800, 1000, 210, 160, 60)).toEqual([5, 10]);
  });
});

describe('F36 sizes per user', () => {
  function memory() {
    const items = new Map();
    return {
      getItem: (key) => (items.has(key) ? items.get(key) : null),
      setItem: (key, value) => items.set(key, String(value)),
      removeItem: (key) => items.delete(key),
      items,
    };
  }

  it('keeps each user their own sizes per grid, and drops values out of range', () => {
    const storage = memory();
    writeSizes(storage, 7, 'advisor', { planW: 240, rows: { total: 60 } });
    expect(readSizes(storage, 7, 'advisor')).toEqual({ planW: 240, rows: { total: 60 } });
    expect(readSizes(storage, 8, 'advisor')).toEqual({ planW: null, rows: {} });
    storage.setItem(storeKey(7), JSON.stringify({ advisor: { planW: MAX_PLAN_PX + 1, rows: { a: MIN_ROW_PX - 1, b: 40 } } }));
    expect(readSizes(storage, 7, 'advisor')).toEqual({ planW: null, rows: { b: 40 } });
  });

  it('↺ Reset sizes removes them, and five plans fit across by default', () => {
    const storage = memory();
    writeSizes(storage, 7, 'advisor', { planW: 240, rows: {} });
    writeSizes(storage, 7, 'advisor', { planW: null, rows: {} });
    expect(storage.items.size).toBe(0);
    expect(fitWidth(1138)).toBe(185);
    expect(fitWidth(100)).toBeNull();
  });
});
