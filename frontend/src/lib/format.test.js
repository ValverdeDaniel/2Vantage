import { describe, expect, it } from 'vitest';
import {
  formatDate,
  formatMoney,
  formatPercent,
  formatRate,
  formatUpdated,
  formatWhen,
  personName,
  toDate,
} from './format';

// plan.md §3.6, §5.4: dates MM/DD/YYYY; money $1,500; rates $512.34; percent +8.0%.
describe('formatDate', () => {
  it('reads a plain day as that calendar day, never shifted by the time zone', () => {
    expect(formatDate('2027-01-01')).toBe('01/01/2027');
    expect(toDate('2027-01-01').getDate()).toBe(1);
  });

  it('shows the fallback for a missing or bad date', () => {
    expect(formatDate('', '—')).toBe('—');
    expect(formatDate('not a date', '—')).toBe('—');
  });
});

describe('money, rates and percentages', () => {
  it.each([
    [1500, {}, '$1,500'],
    ['1,500.49', {}, '$1,500'],
    [17280, { signed: true }, '+$17,280'],
    [-6000, { signed: true }, '−$6,000'],
    ['', { empty: '—' }, '—'],
  ])('formatMoney(%s, %o) is %s', (value, options, text) => {
    expect(formatMoney(value, options)).toBe(text);
  });

  it('shows rates with two decimals, or up to four when asked', () => {
    expect(formatRate(512.3)).toBe('$512.30');
    expect(formatRate('0.185', { decimals: 4 })).toBe('$0.185');
    expect(formatRate(-12)).toBe('−$12.00');
  });

  it('signs percentage points', () => {
    expect(formatPercent(8)).toBe('+8.0%');
    expect(formatPercent(-5)).toBe('−5.0%');
    expect(formatPercent(8, { signed: false })).toBe('8.0%');
  });
});

describe('when something happened', () => {
  const now = new Date(2026, 10, 11, 15, 4);

  it('says Today, Yesterday or the date', () => {
    expect(formatUpdated(new Date(2026, 10, 11, 9, 12), now)).toMatch(/^Today /);
    expect(formatUpdated(new Date(2026, 10, 10, 9, 12), now)).toBe('Yesterday');
    expect(formatUpdated(new Date(2026, 10, 8, 9, 12), now)).toBe('11/08/2026');
    expect(formatWhen(new Date(2026, 10, 10, 9, 12), now)).toMatch(/^Yesterday 9:12/);
  });

  it('names a person, or the fallback', () => {
    expect(personName({ id: 3, name: 'Dana Lee' })).toBe('Dana Lee');
    expect(personName(null)).toBe('Unassigned');
  });
});
