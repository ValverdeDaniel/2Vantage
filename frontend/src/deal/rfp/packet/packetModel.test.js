import { describe, expect, it } from 'vitest';
import { countWords, includeBody, isPick, optimisticTicks, packetSummary, tickBody, triState } from './packetModel';

const row = (key, include, defaultInclude, extra = {}) => ({
  key,
  include,
  default_include: defaultInclude,
  available: true,
  deliberate: '',
  ...extra,
});

const rows = [
  row('census-warner', true, true),
  row('census-aetna', false, true),
  row('census-angle', true, false),
  row('census-angle-csv', false, false, { deliberate: 'The same census' }),
  row('census-uhc', false, false, { available: false }),
];

describe('K35 the packet ticks (packetModel)', () => {
  it('Select all writes only disagreements, a return to the default as null, and leaves off-on-purpose rows', () => {
    expect(includeBody(rows, true)).toEqual({ 'census-aetna': null });
  });

  it('Deselect all empties the packet, sending null where the default is off', () => {
    expect(includeBody(rows, false)).toEqual({ 'census-warner': false, 'census-angle': null });
  });

  it('a single tick sends null when it lands on the default', () => {
    expect(tickBody(rows[1], true)).toEqual({ 'census-aetna': null });
    expect(tickBody(rows[0], false)).toEqual({ 'census-warner': false });
  });

  it('the three-state box counts what can ride, and what is off on purpose', () => {
    const state = triState(rows);
    expect([state.on, state.total, state.offOnPurpose, state.all, state.some]).toEqual([2, 4, 1, false, true]);
    expect(countWords(state)).toBe('2 of 4 in packet · 1 off on purpose');
    const full = triState(rows.map((r) => (r.deliberate ? r : { ...r, include: true })));
    expect(full.all).toBe(true);
  });

  it('marks a pick that differs from the recommendation, never an unavailable row', () => {
    expect(rows.map(isPick)).toEqual([false, true, true, false, false]);
  });

  it('shows a tick at once, and a reset puts every row back on its default', () => {
    const packet = { rows, count: 2 };
    const ticked = optimisticTicks(packet, { 'census-aetna': null, 'census-uhc': true });
    expect(ticked.rows.map((r) => r.include)).toEqual([true, true, true, false, false]);
    expect(ticked.count).toBe(3);
    expect(optimisticTicks(packet, 'reset').count).toBe(2);
    expect(packetSummary({ count: 1 })).toBe('1 document in the packet');
    expect(packetSummary({ count: 0 })).toBe('Nothing ticked yet');
  });
});
