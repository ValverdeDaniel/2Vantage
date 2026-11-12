import { describe, expect, it } from 'vitest';
import {
  chooseLine,
  groupRows,
  isOpen,
  lineOrder,
  moved,
  plansSummary,
  readRowsPref,
  recommendationWords,
  rowSections,
  rowsSummary,
  shownCards,
  stampOf,
  toggledRows,
  writeRowsPref,
} from './builderModel';

const META = {
  cards: [
    { key: 'cover', line: false },
    { key: 'quotes', line: true },
    { key: 'rows', line: true },
    { key: 'markets', line: true },
  ],
  on_screen: ['quotes', 'rows'],
};
const STAMP = { by: 'Pat', at: '2026-11-12T10:00:00' };

function line(over = {}) {
  return {
    line: 'medical',
    label: 'Medical',
    starred: 3,
    quotes: 9,
    pages: 2,
    presented_ids: [1, 2, 3, 4],
    recommendation: { needs_pick: true, plans: [], groups: [], sold: [], covered: false, renewals: [], keepable: [] },
    ...over,
  };
}

describe('J18 the cards on screen, open unless completed', () => {
  it('lists the line cards the builder draws and reads their stamps', () => {
    const cards = shownCards(META, 'dental');
    expect(cards).toEqual([
      { key: 'quotes', line: 'dental' },
      { key: 'rows', line: 'dental' },
    ]);
    const stored = { lines: { dental: { quotes: STAMP } } };
    expect(stampOf(stored, cards[0])).toEqual(STAMP);
    expect(isOpen({}, stored, cards[0])).toBe(false); // a completed card comes back collapsed
    expect(isOpen({}, stored, cards[1])).toBe(true);
    expect(isOpen({ 'dental:quotes': true }, stored, cards[0])).toBe(true);
  });
});

describe('J55 the Plans card says where the line stands', () => {
  it('counts the stars, the pages and the picks', () => {
    expect(plansSummary(line())).toBe('★ 3 on the proposal · 4 plans · 2 pages · No recommendation yet');
    expect(plansSummary(line({ starred: 0, quotes: 0, pages: 0 }))).toBe('No quotes yet · No recommendation yet');
  });

  it('words one pick, several current plans, a kept current plan and a sale', () => {
    const groups = [
      { answered: true, plan_ids: [7] },
      { answered: false, plan_ids: [] },
    ];
    expect(recommendationWords(line({ recommendation: { ...line().recommendation, groups } })).long).toBe(
      '1 of 2 current plans have a recommendation.',
    );
    const keep = { ...line().recommendation, covered: true, plans: [{ words: 'Aetna PPO', keep: true }] };
    expect(recommendationWords(line({ recommendation: keep }))).toMatchObject({
      long: 'We recommend keeping Aetna PPO.',
      open: false,
    });
    const sold = { ...line().recommendation, sold: ['Cigna HDHP'] };
    expect(recommendationWords(line({ recommendation: sold })).long).toBe(
      'Sold: Cigna HDHP. The sold plan is the recommendation.',
    );
  });
});

describe('J62 J61 the rows and card stats a click leaves picked', () => {
  const keys = ['a', 'b', 'c', 'd'];

  it('starts from every row when nothing is picked, and keeps the line order', () => {
    expect(toggledRows(null, keys, 'b')).toEqual(['a', 'c', 'd']);
    expect(toggledRows(['d'], keys, 'a')).toEqual(['a', 'd']);
    expect(groupRows(null, keys, ['a', 'b'], false)).toEqual(['c', 'd']);
    expect(groupRows([], keys, ['c', 'a'], true)).toEqual(['a', 'c']);
    expect(rowsSummary({ rows: null }, 4)).toBe('Every row with a value');
    expect(rowsSummary({ rows: ['a'] }, 4)).toBe('1 of 4 rows');
  });

  it('groups the row picker and moves a stat one place', () => {
    const rows = [
      { key: 'a', group: 'g1', group_label: 'One' },
      { key: 'b', group: 'g1', group_label: 'One' },
      { key: 'c', group: 'g2', group_label: 'Two' },
    ];
    expect(rowSections(rows).map((section) => [section.label, section.rows.length])).toEqual([
      ['One', 2],
      ['Two', 1],
    ]);
    expect(moved(['x', 'y', 'z'], 2, -1)).toEqual(['x', 'z', 'y']);
    expect(moved(['x', 'y'], 0, -1)).toBeNull();
  });
});

describe('J31 the line order and the line shown', () => {
  const lines = [{ line: 'medical' }, { line: 'dental' }, { line: 'vision' }];

  it('moves a line one place and falls back to the first line', () => {
    expect(lineOrder(lines, 'dental', 1)).toEqual(['medical', 'vision', 'dental']);
    expect(lineOrder(lines, 'medical', -1)).toBeNull();
    expect(chooseLine(lines, 'vision')).toBe('vision');
    expect(chooseLine(lines, 'life')).toBe('medical');
    expect(chooseLine([], 'life')).toBe('');
  });
});

describe('J16 Key rows or All rows, per browser', () => {
  it('reads the old key and defaults to Key rows', () => {
    const store = new Map();
    const storage = { getItem: (k) => store.get(k) ?? null, setItem: (k, v) => store.set(k, v) };
    expect(readRowsPref(storage)).toBe('key');
    writeRowsPref(storage, 'all');
    expect(store.get('vantage.bnf.builder.pageRows')).toBe('all');
    expect(readRowsPref(storage)).toBe('all');
    expect(readRowsPref(null)).toBe('key');
  });
});
