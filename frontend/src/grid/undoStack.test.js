import { describe, expect, it } from 'vitest';
import { UNDO_DEPTH, popUndo, pushUndo, undoWrite } from './undoStack';

const entry = (n) => ({ cell: `41|rate_ee`, before: String(n), after: String(n + 1) });

describe('F70 the undo stack', () => {
  it('takes back the newest step first', () => {
    let stack = [];
    stack = pushUndo(stack, entry(1));
    stack = pushUndo(stack, entry(2));
    const first = popUndo(stack);
    expect(first.entry).toEqual(entry(2));
    const second = popUndo(first.stack);
    expect(second.entry).toEqual(entry(1));
    expect(popUndo(second.stack)).toEqual({ entry: null, stack: [] });
  });

  it('keeps 50 steps, dropping the oldest', () => {
    let stack = [];
    for (let n = 0; n < UNDO_DEPTH + 5; n += 1) stack = pushUndo(stack, entry(n));
    expect(UNDO_DEPTH).toBe(50);
    expect(stack).toHaveLength(UNDO_DEPTH);
    expect(stack[0]).toEqual(entry(5));
    expect(stack[stack.length - 1]).toEqual(entry(UNDO_DEPTH + 4));
  });

  it('never changes the stack it was given', () => {
    const stack = [entry(1)];
    pushUndo(stack, entry(2));
    popUndo(stack);
    expect(stack).toEqual([entry(1)]);
  });

  it('J74 writes the earlier value expecting the value the server stored', () => {
    expect(undoWrite({ cell: '41|rate_ee', before: '612.50', after: '640' })).toEqual({
      cell: '41|rate_ee',
      value: '612.50',
      expect: '640',
    });
  });
});
