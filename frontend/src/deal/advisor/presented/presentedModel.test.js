import { describe, expect, it } from 'vitest';
import { pickLine, presentedPlans, quoteFileIds, shortlistWords } from './presentedModel';

const PLANS = [
  { id: 1, role: 'current', starred: false, presented: true },
  { id: 2, role: 'renewal', starred: false, presented: true },
  { id: 3, role: 'alternate', starred: true, presented: true },
  { id: 4, role: 'alternate', starred: false, presented: false },
];

describe('the board in presented mode (J76, J81)', () => {
  it('shows what the proposal presents while the line has a shortlist, else every plan', () => {
    const shortlisted = presentedPlans(PLANS, false);
    expect(shortlisted.shown.map((plan) => plan.id)).toEqual([1, 2, 3]);
    expect(shortlistWords(shortlisted)).toBe('Show all 4 plans');
    const all = presentedPlans(PLANS, true);
    expect(all.shown).toHaveLength(4);
    expect(shortlistWords(all)).toBe('★ Shortlist (1)');
    const none = presentedPlans(PLANS.map((plan) => ({ ...plan, starred: false })), false);
    expect([none.shown.length, shortlistWords(none)]).toEqual([4, null]);
  });

  it('keeps the line asked for when the deal has it', () => {
    const lines = [{ line: 'medical' }, { line: 'dental' }];
    expect(pickLine(lines, 'dental')).toBe('dental');
    expect(pickLine(lines, 'vision')).toBe('medical');
    expect(pickLine([], 'dental')).toBeNull();
  });

  it('re-reads only the quote files, never an issued proposal', () => {
    const meta = { ai: { targets: [{ key: 'quotes', kinds: ['quote', 'renewal'] }] } };
    const docs = [{ id: 1, kind: 'quote' }, { id: 2, kind: 'census' }, { id: 3, kind: 'renewal' }, { id: 4, kind: 'quote', protected: true }];
    expect(quoteFileIds(docs, meta)).toEqual([1, 3]);
    expect(quoteFileIds(docs, {})).toEqual([]);
  });
});
