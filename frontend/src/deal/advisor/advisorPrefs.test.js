import { describe, expect, it } from 'vitest';
import {
  PREFS_KEY,
  chooseFileWanted,
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
    expect(chooseView('stop-loss', null, offeredViews(lines, []))).toBe('quotes'); // no stop-loss line here (F2)
    expect(chooseView('unleashed', null)).toBe('quotes'); // Unleashed waits (F4)
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

describe('F3 F136 the Export viewer is the last view and keeps its file', () => {
  it('offers the Export viewer last, and ?file= wins over the kept file', () => {
    expect(offeredViews(lines, []).at(-1).key).toBe('export');
    expect(chooseView('export', 'quotes')).toBe('export');
    expect(chooseFileWanted('excel', 'powerpoint')).toBe('excel');
    expect(chooseFileWanted(null, 'powerpoint')).toBe('powerpoint');
    expect(chooseFileWanted(null, undefined)).toBe('');
  });
});

describe('F2 the Stop-loss analysis pill shows only with a stop-loss line', () => {
  it('is offered second, as the old app put it, once the deal has the line, even with no plans yet', () => {
    const withLine = [...lines, { line: 'stop_loss', current: 0, renewal: 0, alternate: 0 }];
    expect(offeredViews(lines, [], 'stop_loss').map((view) => view.key)).not.toContain('stop-loss');
    expect(offeredViews(withLine, [], 'stop_loss').map((view) => view.key).slice(0, 2)).toEqual(['quotes', 'stop-loss']);
    expect(offeredViews(withLine, [], undefined).map((view) => view.key)).not.toContain('stop-loss'); // meta not yet
    expect(chooseView('stop-loss', 'quotes', offeredViews(withLine, [], 'stop_loss'))).toBe('stop-loss');
  });
});
