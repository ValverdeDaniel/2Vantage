import { describe, expect, it } from 'vitest';
import { carrierForms } from '../../../lib/findText';
import { blockedWhy, pickerEntries, pickerNote, searchPlaces } from './pickerRows';

// A line with two current plans (1, 2): 3 renews 1; 4 and 5 replace 1 and 2; 6 is off the proposal; 7 a priced version.
const col = (id, extra = {}) => ({ plan_id: id, kind: 'option', links: [], stays_with: null, on: true, why_not: null, ...extra });
const payload = {
  several: true,
  nothing_starred: false,
  presented_ids: [1, 2, 3, 4, 5],
  plans: [
    col(1, { kind: 'current', why_not: 'Current plans lead each page', carrier: 'Aetna', name: 'HDHP', words: 'Aetna HDHP' }),
    col(2, { kind: 'current', why_not: 'Current plans lead each page', carrier: 'Aetna', name: 'PPO', words: 'Aetna PPO' }),
    col(3, { kind: 'renewal', links: [1], stays_with: 1, stays_words: 'Renews Current 1: it stays beside that plan', page: 1 }),
    col(4, { links: [1], carrier: 'Cigna', name: 'LocalPlus', words: 'Cigna LocalPlus', page: 1 }),
    col(5, { links: [2], carrier: 'UnitedHealthcare', name: 'Choice Plus', words: 'UnitedHealthcare Choice Plus', page: 2 }),
  ],
  others: [
    col(6, { on: false, links: [2], carrier: 'Cigna', name: 'Open Access', words: 'Cigna Open Access' }),
    col(7, { on: false, kind: 'priced', why_not: 'Moves with its plan', links: [1] }),
  ],
  pages: [
    { n: 1, part: 'options' },
    { n: 2, part: 'options' },
  ],
  landing: { '': 'Page 2 has room for 4 more plans.', 1: 'Page 1 is full. One more plan starts page 2.' },
  full_words: null,
};
const byId = new Map([...payload.plans, ...payload.others].map((p) => [p.plan_id, p]));

describe('pickerRows (F45, J8, J9, J10)', () => {
  it('lists the proposal in the client order, then the other plans, narrowed by the finder rule', () => {
    expect(pickerEntries(payload, '').map((e) => [e.plan.plan_id, e.on])).toEqual([
      [1, true],
      [2, true],
      [3, true],
      [4, true],
      [5, true],
      [6, false],
      [7, false],
    ]);
    expect(pickerEntries(payload, 'cigna').map((e) => e.plan.plan_id)).toEqual([4, 6]);
    const index = { plans: [{ id: 5, line: 'medical', carrier: 'unitedhealthcare', texts: ['Choice Plus', 'H1234-001'] }] };
    const forms = carrierForms([{ key: 'unitedhealthcare', name: 'UnitedHealthcare', aliases: ['UHC'] }]);
    const places = searchPlaces(index, 'medical');
    expect(pickerEntries(payload, 'uhc', places, forms).map((e) => e.plan.plan_id)).toEqual([5]);
    expect(pickerEntries(payload, 'h1234001', places, forms).map((e) => e.plan.plan_id)).toEqual([5]);
  });

  it('greys the spot itself, current plans and priced versions in the server’s words', () => {
    const spot = byId.get(4);
    expect(blockedWhy(byId.get(4), { spot, payload })).toBe('Here now');
    expect(blockedWhy(byId.get(1), { spot, payload })).toBe('Current plans lead each page');
    expect(blockedWhy(byId.get(7), { spot, payload })).toBe('Moves with its plan');
    expect(blockedWhy(byId.get(6), { spot, payload })).toBe(null); // off the proposal: it replaces the spot's plan
  });

  it('keeps a renewal beside its plan, both ways, as quotes/slots.py does', () => {
    expect(blockedWhy(byId.get(3), { spot: byId.get(5), payload })).toBe('Renews Current 1: it stays beside that plan');
    expect(blockedWhy(byId.get(3), { spot: byId.get(4), payload })).toBe(null); // same plan: no link changes
    expect(blockedWhy(byId.get(5), { spot: byId.get(3), payload })).toBe('The renewal here stays beside its plan');
    expect(blockedWhy(byId.get(6), { spot: byId.get(3), payload })).toBe(null); // the renewal leaves: no relink
    expect(blockedWhy(byId.get(3), { beside: 2, payload })).toBe('Renews Current 1: it stays beside that plan');
    expect(blockedWhy(byId.get(3), { beside: 1, payload })).toBe(null);
    expect(blockedWhy(byId.get(3), { spot: byId.get(5), payload: { ...payload, several: false } })).toBe(null);
  });

  it('refuses a plan off the proposal when adding to a full line', () => {
    const full = { ...payload, full_words: 'The Medical proposal holds 16 plans (2 current, 14 starred) — take one off first.' };
    expect(blockedWhy(byId.get(6), { beside: 2, payload: full })).toMatch(/take one off first/);
    expect(blockedWhy(byId.get(4), { beside: 1, payload: full })).toBe(null); // already on: it only moves
  });

  it('words the note for a pick, an add and a line with nothing starred', () => {
    expect(pickerNote({ spot: byId.get(4), payload, lineLabel: 'Medical' })).toMatch(/^Pick the plan to show in place of LocalPlus/);
    expect(pickerNote({ beside: 1, payload, lineLabel: 'Medical' })).toBe(
      'Add a plan to the Medical proposal. Page 1 is full. One more plan starts page 2. ↑↓ move, Enter picks, Esc closes.',
    );
    expect(pickerNote({ beside: null, payload, lineLabel: 'Medical' })).toMatch(/Page 2 has room for 4 more plans/);
    expect(pickerNote({ payload: { ...payload, nothing_starred: true }, lineLabel: 'Dental' })).toMatch(
      /^Nothing is starred, so every Dental quote already prints/,
    );
    const renewalPage = { ...payload, pages: [{ n: 1, part: 'renewal' }] };
    expect(pickerNote({ spot: byId.get(3), payload: renewalPage, lineLabel: 'Medical' })).toMatch(/takes down the renewal page/);
  });
});
