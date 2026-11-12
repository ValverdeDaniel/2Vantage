import { describe, expect, it } from 'vitest';
import { approveWords, moreKeys, movedFrom, nextOpen, progress, rejectWords } from './queueModel';

const list = [{ id: 'a' }, { id: 'b' }, { id: 'c' }, { id: 'd' }];

describe('L15 the queue moves on after a decision', () => {
  it('skips what was decided or left for later, wrapping round', () => {
    expect(nextOpen(list, 'a', { b: { label: 'Approved' } })).toBe('c');
    expect(nextOpen(list, 'c', {}, new Set(['d']))).toBe('a');
    expect(nextOpen(list, 'a', { b: {}, c: {}, d: {} })).toBe(null);
  });

  it('J and K move one place and hold at the ends', () => {
    expect(movedFrom(list, 'b', 1)).toBe('c');
    expect(movedFrom(list, 'a', -1)).toBe('a');
    expect(movedFrom(list, 'd', 1)).toBe('d');
    expect(movedFrom([], 'a', 1)).toBe(null);
  });
});

describe('L15 the keys say what they do', () => {
  it('A and X in the item’s own words, a blocked X says why', () => {
    expect(approveWords({ approve: 'Approve' })).toMatch(/^Approve \(A\): accept it/);
    expect(rejectWords({ reject: 'Send back', rejectBlocked: 'Not yet.' })).toBe('Not yet.');
    expect(rejectWords({ reject: 'Correct', rejectMode: 'value' })).toMatch(/type the right value/);
  });

  it('? lists the extras, the note and J/K; read-only drops the writes', () => {
    const cfg = { extras: [{ action: 'clear', label: 'Keep ours', key: 'U' }], noteAction: '＋ Note' };
    expect(moreKeys(cfg, false).map(([key]) => key)).toEqual(['U', 'N', 'J', 'K']);
    expect(moreKeys(cfg, true).map(([key]) => key)).toEqual(['J', 'K']);
  });

  it('counts what was reviewed and left for later', () => {
    expect(progress(list, { a: {} }, new Set(['b', 'a']))).toEqual({ done: 1, later: 1, pct: 25 });
    expect(progress([], {}, new Set())).toEqual({ done: 0, later: 0, pct: 0 });
  });
});
