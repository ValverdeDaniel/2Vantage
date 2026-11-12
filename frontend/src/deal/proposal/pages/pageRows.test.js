import { describe, expect, it } from 'vitest';
import { cellText, columnsById, pageColumns, pageHead, pageSections, shownPages } from './pageRows';
import { movedNote, pageMemo } from './pageToast';

const plan = (id, page, extra = {}) => ({ plan_id: id, page, kind: 'option', words: `Carrier Plan ${id}`, ...extra });
const payload = {
  plans: [plan(1, 1, { kind: 'current' }), plan(2, 1), plan(3, 1), plan(4, 2)],
};
const pages = [
  { n: 1, plan_ids: [1, 2, 3], repeat_ids: [], label: 'Cigna', full: false },
  { n: 2, plan_ids: [1, 4], repeat_ids: [1], label: 'UnitedHealthcare', full: false },
];

describe('pageRows (F37, F38, J49)', () => {
  it('lays a page out left to right and marks a plan shown again', () => {
    const byId = columnsById(payload);
    expect(pageColumns(pages[0], byId).map((c) => [c.plan.plan_id, c.place, c.repeated])).toEqual([
      [1, 1, false],
      [2, 2, false],
      [3, 3, false],
    ]);
    expect(pageColumns(pages[1], byId).map((c) => [c.plan.plan_id, c.repeated])).toEqual([
      [1, true],
      [4, false],
    ]);
  });

  it('groups rows under their headings and reads blanks as a dash', () => {
    const rows = [
      { key: 'network', label: 'Network', section: 'Plan info', cells: { 1: 'Open Access', 2: '' } },
      { key: 'plan_type', label: 'Plan Type', section: 'Plan info', cells: { 1: 'HDHP', 2: 'PPO' } },
      { key: 'deductible_single', label: 'Deductible (Single)', section: 'Deductibles & maximums', cells: { 2: '$3,000' } },
    ];
    const sections = pageSections(rows, [payload.plans[0], payload.plans[1]]);
    expect(sections.map((s) => [s.heading, s.rows.map((r) => r.cells)])).toEqual([
      ['Plan info', [['Open Access', '—'], ['HDHP', 'PPO']]],
      ['Deductibles & maximums', [['—', '$3,000']]],
    ]);
    expect(pageSections([{ key: 'a', label: 'A', section: '', cells: {} }], [])[0].heading).toBe(null);
    expect(cellText(null)).toBe('—');
    expect(cellText('$0')).toBe('$0');
  });

  it('folds a line with nothing starred to its first two pages until asked', () => {
    const three = [...pages, { n: 3, plan_ids: [5], repeat_ids: [] }];
    expect(shownPages(three, true, false)).toMatchObject({ folded: true, foldable: true });
    expect(shownPages(three, true, false).pages).toHaveLength(2);
    expect(shownPages(three, true, true)).toMatchObject({ folded: false, foldable: true });
    expect(shownPages(three, false, false)).toMatchObject({ folded: false, foldable: false });
    expect(shownPages(pages, true, false).folded).toBe(false);
  });

  it('heads a page with its count and fullness', () => {
    expect(pageHead({ ...pages[0], full: true, plan_ids: [1, 2, 3, 4, 5, 6] }, 3, 6)).toEqual({
      title: 'Page 1 of 3',
      label: 'Cigna',
      count: '6 of 6 columns · full',
    });
  });
});

describe('pageToast (F38)', () => {
  const byId = columnsById({ plans: [...payload.plans, plan(5, 3, { words: 'Cigna LocalPlus 1000' })] });

  it('names the page a write added and the plan that moved onto it', () => {
    const before = pageMemo('medical', pages);
    const after = [...pages, { n: 3, plan_ids: [1, 5], repeat_ids: [1] }];
    expect(movedNote(before, 'medical', after, byId, 'Medical')).toBe(
      'Medical now runs to 3 comparison pages: Cigna LocalPlus 1000 moved to page 3.',
    );
  });

  it('says nothing on the first read, another line, or when no page is added', () => {
    expect(movedNote(null, 'medical', pages, byId, 'Medical')).toBe('');
    expect(movedNote(pageMemo('dental', pages), 'medical', [...pages, pages[1]], byId, 'Medical')).toBe('');
    expect(movedNote(pageMemo('medical', pages), 'medical', pages, byId, 'Medical')).toBe('');
  });
});
