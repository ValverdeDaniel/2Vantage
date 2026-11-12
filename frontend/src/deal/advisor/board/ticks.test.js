import { describe, expect, it } from 'vitest';
import { batch, markBlock, moveBlock, selectable, tickBlock, withVersions } from './ticks';

const p = (id, role, extra = {}) => ({ id, role, starred: false, sold: false, ...extra });
const plans = [
  p(1, 'current'),
  p(2, 'alternate', { starred: true }),
  p(3, 'alternate'),
  p(4, 'alternate', { derived_from: 3, derived: { kind: 'duplicate' } }),
  p(5, 'renewal', { sold: true }),
];

describe('F57 F58 ticks and the batch star', () => {
  it('greys a current plan outside Edit, and every row is live in Edit', () => {
    expect(tickBlock(plans[0], false)).toMatch(/takes no star/);
    expect(tickBlock(plans[0], true)).toBe('');
    expect(tickBlock(plans[2], false)).toBe('');
  });

  it('select-all takes the quotes shown, never the current plans', () => {
    expect(selectable([plans[1], plans[2]], false)).toEqual([2, 3]);
  });

  it('★ Star takes the unstarred quotes and ☆ Unstar the starred ones', () => {
    const { toStar, toUnstar } = batch([plans[0], plans[1], plans[2]], plans);
    expect(toStar).toEqual([3]);
    expect(toUnstar).toEqual([2]);
  });
});

describe('F53 F59 F60 what Edit actions take', () => {
  it('Move to leaves sold plans, copies and their originals', () => {
    const versioned = withVersions(plans);
    expect(moveBlock(plans[4], versioned)).toMatch(/^Sold/);
    expect(moveBlock(plans[3], versioned)).toMatch(/stays on its original/);
    expect(moveBlock(plans[2], versioned)).toMatch(/remove them before moving it/);
    expect(batch(plans, plans).toMove).toEqual([1, 2]);
  });

  it('Mark current takes quotes that are not sold; Remove current the current plans; Delete every tick', () => {
    expect(markBlock(plans[0])).toBe('Already a current plan');
    expect(markBlock(plans[3])).toBe(''); // a duplicate is a plan of its own (D-049)
    const actions = batch(plans, plans);
    expect(actions.toMark).toEqual([2, 3, 4]);
    expect(actions.toUnset).toEqual([1]);
    expect(actions.toRemove).toEqual([1, 2, 3, 4, 5]);
  });
});
