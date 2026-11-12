import { describe, expect, it } from 'vitest';
import { carrierForms, findTerms } from '../../../lib/findText';
import { gridFind, onlyMatches } from './gridFind';
import { buildStationGrid, cellAt, filterGrid, gridShape } from './stationModel';

const META = {
  groups: [
    { key: 'info', label: 'Plan info' },
    { key: 'deduct', label: 'Deductibles & maximums' },
    { key: 'den_ben', label: 'Dental benefits' },
    { key: 'rates', label: 'Monthly rates' },
  ],
  fields: [
    { key: 'plan_type', label: 'Plan Type', type: 'text' },
    { key: 'deductible_single', label: 'Deductible (Single)', type: 'amount' },
    { key: 'den_annual_max', label: 'Annual Max', type: 'amount' },
    { key: 'rate_ee', label: 'Rate — EE', type: 'rate' },
  ],
  line_groups: {
    medical: [
      { key: 'info', fields: ['plan_type'] },
      { key: 'deduct', fields: ['deductible_single'] },
      { key: 'rates', fields: ['rate_ee'] },
    ],
    dental: [
      { key: 'info', fields: ['plan_type'] },
      { key: 'den_ben', fields: ['den_annual_max'] },
      { key: 'rates', fields: ['rate_ee'] },
    ],
  },
};
const QUOTE = 7; // the file in scope
const RENEWAL = 8; // another file
const plan = (id, carrier, name, values, cells) => ({ id, carrier, name, role: 'alternate', values, cells });
const MEDICAL = {
  line: 'medical',
  documents: [
    { id: QUOTE, name: 'quote.xlsx' },
    { id: RENEWAL, name: 'renewal.pdf' },
  ],
  plans: [
    plan(1, 'Aetna', 'HMO 1000', { rate_ee: '480' }, { rate_ee: { d: 1 } }),
    plan(2, 'UnitedHealthcare', 'Choice Plus HDHP 3300', { plan_type: 'HDHP', deductible_single: '3300', rate_ee: '512.34' }, {
      plan_type: { d: 0 },
      deductible_single: { d: 0, s: 'to_check' },
      rate_ee: { d: 1 },
    }),
    plan(3, 'Cigna', 'LocalPlus 1000', { deductible_single: '1000', rate_ee: '498' }, { deductible_single: { d: 0, p: 1 } }),
    plan(4, 'Cigna', 'Typed only', { rate_ee: '400' }, {}),
  ],
};
const DENTAL = {
  line: 'dental',
  documents: [{ id: QUOTE, name: 'quote.xlsx' }],
  plans: [plan(5, 'Delta Dental', 'PPO 1500', { den_annual_max: '1500' }, { den_annual_max: { d: 0 } })],
};
const model = buildStationGrid({ comparisons: [MEDICAL, DENTAL], meta: META, scopeIds: new Set([QUOTE]) });

describe('E36–E41 the station grid', () => {
  it('E36 E37 shows the plans read from the files in scope, line by line in the server’s order', () => {
    expect(model.plans.map((p) => [p.id, p.line])).toEqual([
      [2, 'medical'],
      [3, 'medical'],
      [5, 'dental'],
    ]);
  });

  it('E38 joins the lines’ fields in group order, one band per group', () => {
    expect(model.sections.map((s) => [s.group, s.rows.map((r) => r.key)])).toEqual([
      ['info', ['plan_type']],
      ['deduct', ['deductible_single']],
      ['den_ben', ['den_annual_max']],
      ['rates', ['rate_ee']],
    ]);
    expect(gridShape(model)).toEqual({
      rows: ['plan_type', 'deductible_single', 'den_annual_max', 'rate_ee'],
      cols: ['2', '3', '5'],
    });
  });

  it('E41 knows each value’s file: this one, another, or none (typed); and where a field does not apply', () => {
    expect(cellAt(model, 'plan_type', 2)).toMatchObject({ raw: 'HDHP', doc: QUOTE, here: true, applies: true });
    expect(cellAt(model, 'rate_ee', 2)).toMatchObject({ doc: RENEWAL, docName: 'renewal.pdf', here: false });
    expect(cellAt(model, 'rate_ee', 3)).toMatchObject({ raw: '498', doc: null, here: false, ref: 'plan:3:rate_ee' });
    expect(cellAt(model, 'den_annual_max', 2).applies).toBe(false);
  });

  it('E40 E50 counts potential errors from these files, and filters to them', () => {
    expect([...model.issues]).toEqual([
      [2, 1],
      [3, 1],
    ]);
    expect(filterGrid(model, { errorsOnly: true }).plans.map((p) => p.id)).toEqual([2, 3]);
    const rows = filterGrid(model, { rowsOnly: true }).sections.flatMap((s) => s.rows.map((r) => r.key));
    expect(rows).toEqual(['deductible_single']);
  });
});

describe('E60–E64 Find on the grid', () => {
  const forms = carrierForms([{ key: 'united_healthcare', name: 'UnitedHealthcare', aliases: ['UHC'] }]);
  const index = new Map([[2, { texts: ['Choice Plus HDHP 3300', 'UnitedHealthcare', 'HDHP'], carrier: 'united_healthcare' }]]);
  const find = (query, view = model) => gridFind(model, view, findTerms(query, forms), index);

  it('E62 E64 a head answers to its carrier’s nickname: one hit per plan, not per value', () => {
    expect(find('UHC').hits.map((h) => h.key)).toEqual(['@head|2']);
  });

  it('E61 E63 hits run heads first, then each row from its label across, at the most specific place', () => {
    expect(find('hdhp').hits.map((h) => h.key)).toEqual(['@head|2', 'plan_type|2']);
    expect(find('deductible').hits.map((h) => h.key)).toEqual(['deductible_single|@label']);
    expect(find('cigna deductible').hits.map((h) => h.key)).toEqual(['deductible_single|3']);
    expect(find('1,000').hits.map((h) => h.key)).toEqual(['@head|3', 'deductible_single|3']);
    expect(find('').hits).toEqual([]);
  });

  it('E63 "Only matches" keeps the plans and rows with a hit; a label hit keeps every plan', () => {
    const narrowed = onlyMatches(model, find('cigna deductible'));
    expect(narrowed.plans.map((p) => p.id)).toEqual([3]);
    expect(narrowed.sections.map((s) => s.group)).toEqual(['deduct']);
    expect(onlyMatches(model, find('deductible')).plans).toHaveLength(3);
    expect(onlyMatches(model, find('nothing here'))).toEqual({ plans: model.plans, sections: model.sections });
  });
});
