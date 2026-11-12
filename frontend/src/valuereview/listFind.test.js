import { describe, expect, it } from 'vitest';
import { carrierForms, findTerms } from '../lib/findText';
import { listHits, listShown } from './listFind';

const forms = carrierForms([{ key: 'united_healthcare', name: 'UnitedHealthcare', aliases: ['UHC'] }]);
const terms = (query) => findTerms(query, forms);
const row = (ref, label, sub, value, plan) => ({ ref, label, sub, value, plan_id: plan });
const rows = [
  row('plan:1:rate_ee', 'Rate — EE', 'UnitedHealthcare · Choice Plus', '530', 1),
  row('plan:2:deductible_single', 'Deductible (Single)', 'Cigna · Open Access', '1500', 2),
  row('plan:1:deductible_single', 'Deductible (Single)', 'UnitedHealthcare · Choice Plus', '2000', 1),
];
const carriers = { 1: 'united_healthcare', 2: 'cigna' };
const opts = { valueOf: (r) => (r.key === 'x' ? '' : `$${r.value}`), carrierOf: (r) => carriers[r.plan_id] };

describe('E63 Find on the List', () => {
  it('matches the loaded rows in the List’s order, by field, plan, value and carrier nickname', () => {
    expect(listHits(rows, terms('deductible'), opts)).toEqual(['plan:2:deductible_single', 'plan:1:deductible_single']);
    expect(listHits(rows, terms('UHC deductible'), opts)).toEqual(['plan:1:deductible_single']);
    expect(listHits(rows, terms('$1,500'), opts)).toEqual(['plan:2:deductible_single']);
    expect(listHits(rows, terms(''), opts)).toEqual([]);
  });

  it('"Only matches" lists just those, or every row when nothing matches', () => {
    expect(listShown(rows, ['plan:1:rate_ee'], true).map((r) => r.ref)).toEqual(['plan:1:rate_ee']);
    expect(listShown(rows, [], true)).toBe(rows);
    expect(listShown(rows, ['plan:1:rate_ee'], false)).toBe(rows);
  });
});
