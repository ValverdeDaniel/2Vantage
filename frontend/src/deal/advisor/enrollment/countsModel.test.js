import { describe, expect, it } from 'vitest';
import {
  badKeys,
  basisText,
  bodyFor,
  buttonLabel,
  candidates,
  countsText,
  initialChoice,
  initialPicked,
  namesBody,
  namesOf,
  rowProblem,
  sourceWords,
} from './countsModel';

const TIERS = ['EE', 'ES', 'EC', 'FAM'];
const plan = (id, extra = {}) => ({ id, carrier: 'Aetna', name: `Plan ${id}`, role: 'alternate', ...extra });

describe('the counts card (F85, F88, F90–F92)', () => {
  it('F85 never offers a priced version, but offers a duplicate', () => {
    const plans = [plan(1), plan(2, { derived_from: 1, derived: { kind: 'concession' } }), plan(3, { derived_from: 1, derived: { kind: 'duplicate' } })];
    expect(candidates(plans).map((p) => p.id)).toEqual([1, 3]);
  });

  it('F85 starts with the plans that carry counts, plus the ones asked for', () => {
    const plans = [plan(1, { enrollment: { EE: 4 } }), plan(2, { enrollment: {} }), plan(3)];
    expect(initialPicked(plans, [3])).toEqual([1, 3]);
  });

  it('F85 counts are whole people; a volume may carry cents; an empty row needs someone', () => {
    expect(badKeys({ EE: '4', ES: '2.5', EC: 'x', FAM: '' }, TIERS)).toEqual(['ES', 'EC']);
    expect(badKeys({ volume: '1,250,000.50' }, ['volume'])).toEqual([]);
    expect(rowProblem({ EE: '', ES: '0' }, TIERS)).toBe('Enter at least one person');
    expect(rowProblem({ EE: '3' }, TIERS)).toBe('');
  });

  it('F88 saves the whole per-plan set, and the line figure only where the card offers it', () => {
    const rows = { 1: { EE: '12', ES: '3', EC: '', FAM: '1' } };
    const figure = { EE: '', ES: '', EC: '', FAM: '' };
    expect(bodyFor({ keys: TIERS, picked: [1], rows, figure, offersFigure: false, on: true })).toEqual({
      on: true,
      plans: [{ id: 1, enrollment: { EE: 12, ES: 3, EC: 0, FAM: 1 } }],
    });
    expect(bodyFor({ keys: TIERS, picked: [], rows, figure: { EE: '20' }, offersFigure: true, on: true }).whole_line).toEqual({
      EE: 20,
      ES: 0,
      EC: 0,
      FAM: 0,
    });
    expect(bodyFor({ keys: TIERS, picked: [], rows, figure, offersFigure: true, on: false }).whole_line).toEqual({});
  });

  it('F92 words lives and volume, and the button follows the basis', () => {
    expect(countsText({ EE: 20, ES: 5, EC: 0, FAM: 2 }, TIERS)).toBe('20 EE · 5 ES · 2 FAM');
    expect(countsText({ lives: 52 }, ['lives'])).toBe('52 lives');
    const block = { keys: ['lives'], typed_plans: 0, figure: null, on: true };
    expect(buttonLabel(block, 'Telehealth')).toBe('＋ Add summary telehealth lives');
    expect(buttonLabel({ keys: TIERS, typed_plans: 2, figure: { EE: 1 }, on: false }, 'Medical')).toBe('Summary tiers · Off (3)');
  });

  it('F89 says what the census counts under the card', () => {
    const block = { keys: TIERS, census: { figures: { EE: 27, ES: 8, EC: 5, FAM: 8 }, source: 'proxy' } };
    expect(basisText(block, 'Accident')).toBe('The medical census counts 27 EE · 8 ES · 5 EC · 8 FAM on Accident.');
    expect(basisText({ keys: TIERS, census: null }, 'Medical')).toBe('No census counts on Medical yet.');
  });

  it('F88 names the plans that lost their price, three then "and N more"', () => {
    const plans = [1, 2, 3, 4, 5].map((id) => plan(id));
    expect(namesOf(plans, [1, 2])).toBe('Aetna Plan 1 and Aetna Plan 2');
    expect(namesOf(plans, [1, 2, 3, 4, 5])).toBe('Aetna Plan 1, Aetna Plan 2, Aetna Plan 3 and 2 more');
  });

  it('F90 saves only the census names a person matched, per current plan', () => {
    const texts = [
      { text: 'PPO 2500', plan_id: 1, how: 'name' },
      { text: 'PPO (old)', plan_id: null, how: null },
      { text: 'HMO typed', plan_id: 2, how: 'hand' },
    ];
    const currents = [plan(1, { role: 'current' }), plan(2, { role: 'current' })];
    const choice = initialChoice(texts);
    expect(namesBody(texts, currents, choice)).toBeNull();
    expect(namesBody(texts, currents, { ...choice, 'PPO (old)': 1 })).toEqual({ 1: ['PPO (old)'], 2: ['HMO typed'] });
    expect(namesBody(texts, currents, { ...choice, 'HMO typed': '' })).toEqual({ 1: [], 2: [] });
  });

  it('F86 reads the source words from /api/meta/', () => {
    const meta = { enrollment: { sources: [{ key: 'proxy', label: 'Borrowed from medical', mark: 'borrowed' }] } };
    expect(sourceWords(meta)).toEqual({ proxy: { label: 'Borrowed from medical', mark: 'borrowed' } });
  });
});
