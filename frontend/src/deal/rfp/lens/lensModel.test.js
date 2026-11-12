import { describe, expect, it } from 'vitest';
import { badgeOf, chipSub, fillBar, notSentWords, readinessCards, rowsWords, statusWords } from './lensModel';

const format = (key, extra = {}) => ({
  key,
  kind: 'census',
  rows: 4,
  columns: 24,
  gaps: 0,
  in_packet: false,
  required_by: [],
  ...extra,
});

describe('K79 K80 the lens words (lensModel)', () => {
  it('shows the files the request sends, else every format', () => {
    const formats = [format('a'), format('b', { in_packet: true }), format('c', { required_by: ['Aetna'] })];
    expect(readinessCards(formats).cards.map((f) => f.key)).toEqual(['b', 'c']);
    expect(readinessCards([format('a')])).toEqual({ cards: [format('a')], sent: false });
  });

  it('says ready, or how many things to fix', () => {
    expect(statusWords({ to_fix: 0 }).text).toBe('✓ Ready to export');
    expect(statusWords({ to_fix: 2 })).toEqual({ text: '2 things to fix', tone: 'gap' });
    expect(statusWords({ to_fix: null }).tone).toBe('');
  });

  it("writes a chip's counts and a card's cap", () => {
    expect(chipSub(format('u', { gaps: 3, in_packet: true }))).toBe(
      "4 rows · 24 columns · 3 we don't store · in the packet",
    );
    expect(rowsWords({ rows: 300, capped: true, max_rows: 213 })).toBe('300 rows · room for 213');
    expect(badgeOf('UnitedHealthcare')).toBe('UHC');
    expect(badgeOf('Oscar Health')).toBe('OH');
  });

  it("draws a column's fill over the rows it applies to (K87)", () => {
    expect(fillBar({ expected: 0 })).toBeNull();
    expect(fillBar({ expected: 4, blank: 1, carrier_required: true })).toEqual({ have: 3, pct: 75, short: true });
  });

  it('counts the columns we never write and their formulas (K88)', () => {
    const notSent = { unwritten_banner: 'Enrollment', columns: [{ formula: true }, { formula: false }] };
    expect(notSentWords(notSent)).toBe('2 columns (“Enrollment”), 1 of them their own formulas');
    expect(notSentWords({})).toBe('');
  });
});
