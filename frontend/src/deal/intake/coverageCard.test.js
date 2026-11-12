import { describe, expect, it } from 'vitest';
import {
  attachChanges,
  cardState,
  gapWords,
  inForceState,
  isCollapsed,
  rememberCollapsed,
  shownKinds,
  tallyWords,
  toggleLineChanges,
  yearState,
} from './coverageCard';

const row = (line, extra = {}) => ({ line, answered: true, in_force: true, this_year: 'market', ...extra });

function memoryStorage(initial = {}) {
  const items = { ...initial };
  return {
    getItem: (key) => (key in items ? items[key] : null),
    setItem: (key, value) => {
      items[key] = value;
    },
  };
}

describe('the card state and its words (B20)', () => {
  it('reads the state and falls back to not confirmed', () => {
    expect(cardState({ state: 'stale' }).badge).toBe('⚠ Changed since confirmed');
    expect(cardState({ state: 'done' }).cls).toBe('bnf-cvg-done');
    expect(cardState(undefined).badge).toBe('Not confirmed yet');
  });

  it('names the gaps and the tally', () => {
    const intent = { counts: { unanswered: 1, shopping: 2, keep: 1, new: 0 }, documents_missing: 2 };
    expect(gapWords(intent)).toEqual(['1 unanswered', '2 documents missing']);
    expect(gapWords({ counts: {}, documents_missing: 1 })).toEqual(['1 document missing']);
    expect(tallyWords({ ...intent, documents_expected: 6, documents_on_file: 4 })).toBe(
      '2 shopping · 1 kept as-is · 0 new · 4/6 documents',
    );
  });
});

describe('the select-all headers (B18)', () => {
  it('counts an unanswered row as not in force', () => {
    expect(inForceState([row('medical'), row('dental', { answered: false, in_force: false })])).toBe('mixed');
    expect(inForceState([row('medical')])).toBe('on');
    expect(inForceState([])).toBe('off');
  });

  it('reads a year column over answered rows only', () => {
    const rows = [row('medical'), row('dental', { this_year: 'keep' }), row('vision', { answered: false })];
    expect(yearState(rows, 'market')).toBe('mixed');
    expect(yearState(rows, 'off')).toBe('');
    expect(yearState([row('vision', { answered: false })], 'market')).toBe('off');
  });
});

describe('document chips and the picker (B21)', () => {
  const kinds = ['renewal', 'invoice', 'sbc'];

  it('shows every kind on a line in force and only files on file otherwise', () => {
    expect(shownKinds(row('medical'), kinds)).toEqual(kinds);
    const gap = row('std', { in_force: false, documents: { renewal: [], invoice: [4], sbc: [] } });
    expect(shownKinds(gap, kinds)).toEqual(['invoice']);
  });

  it('attaches a file by narrowing an unscoped one and re-filing it in one PATCH', () => {
    expect(attachChanges({ kind: 'other', lines: [] }, 'dental', 'invoice')).toEqual({
      lines: ['dental'],
      kind: 'invoice',
    });
    expect(attachChanges({ kind: 'invoice', lines: ['medical'] }, 'dental', 'invoice')).toEqual({
      lines: ['medical', 'dental'],
    });
    expect(attachChanges({ kind: 'invoice', lines: ['dental'] }, 'dental', 'invoice')).toBeNull();
  });

  it('never ticks a file down to no lines, which would read as every line', () => {
    const all = ['medical', 'dental', 'vision'];
    expect(toggleLineChanges({ lines: [] }, 'dental', all)).toEqual({ lines: ['medical', 'vision'] });
    expect(toggleLineChanges({ lines: ['dental'] }, 'dental', all)).toBeNull();
    expect(toggleLineChanges({ lines: ['dental'] }, 'vision', all)).toEqual({ lines: ['dental', 'vision'] });
  });
});

describe('collapse remembered per deal (B23)', () => {
  it('keeps an entry only for a collapsed deal and reads anything else as open', () => {
    const storage = memoryStorage({ 'vantage.bnf.coverage': 'not json' });
    expect(isCollapsed(storage, 31)).toBe(false);
    rememberCollapsed(storage, 31, true);
    expect(isCollapsed(storage, 31)).toBe(true);
    expect(isCollapsed(storage, 32)).toBe(false);
    rememberCollapsed(storage, 31, false);
    expect(storage.getItem('vantage.bnf.coverage')).toBe('{}');
  });
});
