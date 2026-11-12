import { describe, expect, it } from 'vitest';
import { confirmWords, doneText, restoredCount, reviewToast, targetWords, undoneText } from './reviewWords';
import { keyAction } from './keys';

describe('the review words (E48, E52, E54, D126)', () => {
  it('E48 says what a review did, and when it did nothing', () => {
    expect(reviewToast('approve', 3, 'the 2 ticked plans')).toBe('3 values approved on the 2 ticked plans');
    expect(reviewToast('check', 1)).toBe('1 value flagged as needing checking');
    expect(reviewToast('ignore', 0, 'this file')).toBe('Nothing to ignore on this file');
  });

  it('D126 asks before a key acts on more than 25 values; buttons never ask', () => {
    expect(confirmWords('approve', 26, { fromKey: true })).toBe('Approve 26 values?');
    expect(confirmWords('approve', 25, { fromKey: true })).toBe('');
    expect(confirmWords('approve', 400)).toBe('');
  });

  it('E54 names what came back and what changed since', () => {
    expect(doneText({ action: 'ignore', changed: 2 })).toBe('✓ 2 values ignored');
    expect(doneText(null)).toBe('');
    const changes = [{ t: 'plan:1', k: { 'mark.rate_ee': [{}, null], 'mark.rate_fam': [{}, null] } }];
    expect(restoredCount(changes)).toBe(2);
    expect(undoneText(2, 1)).toBe('Undone — 2 values back as before; 1 changed since and was left as it is');
    expect(undoneText(1)).toBe('Undone — 1 value back as before');
  });

  it('F65 names the strip’s target: ticked, filtered, else the line', () => {
    expect(targetWords({ ticked: 2 })).toBe('the 2 ticked plans');
    expect(targetWords({ filtered: 1 })).toBe('the 1 plan the filters show');
    expect(targetWords({ line: 'Medical' })).toBe('every plan on Medical');
    expect(targetWords({ files: 3 })).toBe('these 3 files');
  });
});

describe('the review keys (E55, D124)', () => {
  const press = (key, extra = {}) => ({ key, target: { nodeType: 1, tagName: 'DIV' }, ...extra });

  it('E55 maps A, I, C, U and F to their actions', () => {
    expect(['a', 'I', 'c', 'u', 'f'].map((key) => keyAction(press(key)))).toEqual([
      'approve',
      'ignore',
      'check',
      'clear',
      'find',
    ]);
  });

  it('E55 never takes a key while typing, with a modifier, on repeat or already handled', () => {
    expect(keyAction(press('a', { target: { nodeType: 1, tagName: 'INPUT' } }))).toBeNull();
    expect(keyAction(press('a', { target: { nodeType: 1, tagName: 'DIV', isContentEditable: true } }))).toBeNull();
    expect(keyAction(press('a', { ctrlKey: true }))).toBeNull();
    expect(keyAction(press('a', { repeat: true }))).toBeNull();
    expect(keyAction(press('a', { defaultPrevented: true }))).toBeNull();
    expect(keyAction(press('x'))).toBeNull();
  });
});
