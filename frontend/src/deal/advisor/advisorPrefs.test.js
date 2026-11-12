import { describe, expect, it } from 'vitest';
import {
  PREFS_KEY,
  chooseLayout,
  chooseLine,
  chooseOrientation,
  chooseView,
  offeredViews,
  readPrefs,
  writePrefs,
} from './advisorPrefs';

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
    expect(chooseView('build', 'quotes')).toBe('build'); // the Proposal builder (slice 25)
    expect(chooseOrientation('cols')).toBe('cols');
    expect(chooseOrientation('sideways')).toBe('rows');
  });
});

describe('F37 ▦ Pages is kept per browser, as the old app kept it', () => {
  it('reads the old key’s layout: pages, else the board', () => {
    expect(chooseLayout('pages')).toBe('pages');
    expect(chooseLayout('grid')).toBe('grid');
    expect(chooseLayout(undefined)).toBe('grid');
  });
});

describe('F42 "As quoted" is offered once a read has landed a printed table', () => {
  it('offers the pill only with a printed table, and falls back to Quote comparison without one', () => {
    const keys = (quoted) => offeredViews(lines, quoted).map((view) => view.key);
    expect(keys([])).not.toContain('quoted');
    expect(keys(undefined)).not.toContain('quoted');
    expect(keys([{ document: 7, line: 'medical' }])).toContain('quoted');
    expect(chooseView('quoted', null, offeredViews(lines, []))).toBe('quotes');
    expect(chooseView('quoted', null, offeredViews(lines, [{ document: 7, line: 'medical' }]))).toBe('quoted');
  });
});
