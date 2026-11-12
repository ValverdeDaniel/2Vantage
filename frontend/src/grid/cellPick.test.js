import { describe, expect, it } from 'vitest';
import { allKeys, cellOf, dragPick, keyOf, lineKeys, pickedCells, rectKeys, stepCell } from './cellPick';

const R = ['rate_ee', 'rate_es', 'rate_fam'];
const C = ['41', '42', '43'];

describe('E51 picking cells', () => {
  it('a drag picks the rectangle between two cells, whichever way it runs', () => {
    expect(rectKeys(R, C, { r: 'rate_es', c: '43' }, { r: 'rate_ee', c: '42' })).toEqual([
      'rate_ee|42',
      'rate_ee|43',
      'rate_es|42',
      'rate_es|43',
    ]);
    expect(rectKeys(R, C, { r: 'gone', c: '41' }, { r: 'rate_ee', c: '41' })).toEqual([]);
  });

  it('Ctrl+drag adds to the pick, and dragging from a picked cell takes cells away', () => {
    const base = new Set(['rate_fam|41']);
    const added = dragPick(R, C, base, { r: 'rate_ee', c: '41' }, { r: 'rate_ee', c: '42' });
    expect([...added].sort()).toEqual(['rate_ee|41', 'rate_ee|42', 'rate_fam|41']);
    const dropped = dragPick(R, C, added, { r: 'rate_ee', c: '41' }, { r: 'rate_ee', c: '41' }, false);
    expect(dropped.has('rate_ee|41')).toBe(false);
    expect(base.size).toBe(1);
  });

  it('a header picks a column and a label a row', () => {
    expect(lineKeys(R, C, { c: '42' })).toEqual(['rate_ee|42', 'rate_es|42', 'rate_fam|42']);
    expect(lineKeys(R, C, { r: 'rate_fam' })).toEqual(['rate_fam|41', 'rate_fam|42', 'rate_fam|43']);
  });

  it('Ctrl+A picks every cell; the arrows step and stop at the edges', () => {
    expect(allKeys(R, C)).toHaveLength(9);
    expect(allKeys([], C)).toEqual([]);
    expect(stepCell(R, C, { r: 'rate_ee', c: '41' }, -1, 1)).toEqual({ r: 'rate_ee', c: '42' });
    expect(stepCell(R, C, { r: 'rate_fam', c: '43' }, 1, 1)).toEqual({ r: 'rate_fam', c: '43' });
  });

  it('lists the picked cells on screen in screen order, and reads keys back', () => {
    const picks = new Set(['rate_fam|41', 'rate_ee|43', 'gone|41']);
    expect(pickedCells(R, C, picks)).toEqual([
      { r: 'rate_ee', c: '43' },
      { r: 'rate_fam', c: '41' },
    ]);
    expect(cellOf(keyOf('plan:41', 'a|b'))).toEqual({ r: 'plan:41', c: 'a|b' });
  });
});
