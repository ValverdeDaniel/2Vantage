import { describe, expect, it } from 'vitest';
import { changeWords, holeWords, inactive, yearGroups } from './bookView';

const BOOK = {
  rows: [
    { id: 5, carrier: 'Cigna', status: 'booked' },
    { id: 6, carrier: 'UnitedHealthcare', status: 'booked' },
    { id: 2, carrier: 'Aetna', status: 'renewed' },
  ],
  years: [
    { key: '2027', label: '2027', records: [5, 6], expected: 20490.6, change_pct: 12 },
    { key: '2026', label: '2026', records: [2], expected: 18295, change_pct: null },
  ],
};

describe('the client Commissions tab (CL25)', () => {
  it('groups the records by plan year, newest first, in the server order', () => {
    const groups = yearGroups(BOOK);
    expect(groups.map((group) => group.label)).toEqual(['2027', '2026']);
    expect(groups[0].rows.map((row) => row.carrier)).toEqual(['Cigna', 'UnitedHealthcare']);
    expect(yearGroups(undefined)).toEqual([]);
  });

  it('words the change against the year below, from the server figure', () => {
    const [newer, older] = BOOK.years;
    expect(changeWords(newer, older)).toBe('▲ 12% vs 2026');
    expect(changeWords({ change_pct: -3 }, older)).toBe('▼ 3% vs 2026');
    expect(changeWords(older, undefined)).toBe('');
  });

  it('marks a record no longer live and counts the holes', () => {
    const meta = { commission: { live_statuses: ['booked', 'active'] } };
    expect(inactive(BOOK.rows[2], meta)).toBe(true);
    expect(inactive(BOOK.rows[0], meta)).toBe(false);
    expect(holeWords(1)).toBe('1 hole');
    expect(holeWords(2)).toBe('2 holes');
  });
});
