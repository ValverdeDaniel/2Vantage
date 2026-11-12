import { describe, expect, it } from 'vitest';
import { PREFS_KEY, chooseLine, chooseOrientation, chooseView, readPrefs, writePrefs } from './advisorPrefs';

function memory() {
  const items = new Map();
  return {
    getItem: (key) => (items.has(key) ? items.get(key) : null),
    setItem: (key, value) => items.set(key, String(value)),
  };
}
const lines = [{ line: 'medical' }, { line: 'dental' }];

describe('F1 F5 the kept choices', () => {
  it('keeps the view, line and layout per browser under the old key', () => {
    const storage = memory();
    writePrefs(storage, { line: 'dental' });
    writePrefs(storage, { orientation: 'cols' });
    expect(readPrefs(storage)).toEqual({ line: 'dental', orientation: 'cols' });
    expect(JSON.parse(storage.getItem(PREFS_KEY))).toEqual({ line: 'dental', orientation: 'cols' });
    storage.setItem(PREFS_KEY, 'not json');
    expect(readPrefs(storage)).toEqual({});
  });

  it('?line= wins, then the kept line, and a line the deal lacks falls back to its first', () => {
    expect(chooseLine('dental', 'medical', lines)).toBe('dental');
    expect(chooseLine(null, 'dental', lines)).toBe('dental');
    expect(chooseLine('vision', 'life', lines)).toBe('medical');
    expect(chooseLine(null, null, [])).toBe('');
  });

  it('an unavailable view falls back to Quote comparison', () => {
    expect(chooseView('stop-loss', null)).toBe('quotes');
    expect(chooseView(null, 'quotes')).toBe('quotes');
    expect(chooseOrientation('cols')).toBe('cols');
    expect(chooseOrientation('sideways')).toBe('rows');
  });
});
