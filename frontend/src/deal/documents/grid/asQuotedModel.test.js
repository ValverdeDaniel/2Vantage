import { describe, expect, it } from 'vitest';
import { carrierForms, findTerms } from '../../../lib/findText';
import { PRINTED, buildAsQuoted, printedWhere } from './asQuotedModel';
import { gridFind } from './gridFind';
import { cellAt, gridShape } from './stationModel';

const META = {
  fields: [
    { key: 'plan_type', label: 'Plan Type', type: 'text' },
    { key: 'deductible_single', label: 'Deductible (Single)', type: 'amount' },
    { key: 'deductible_family', label: 'Deductible (Family)', type: 'amount' },
    { key: 'rate_ee', label: 'Rate — EE', type: 'rate' },
  ],
  line_groups: {
    medical: [
      { key: 'info', fields: ['plan_type'] },
      { key: 'deduct', fields: ['deductible_single', 'deductible_family'] },
      { key: 'rates', fields: ['rate_ee'] },
    ],
  },
};
const FILE = 7;
const plan = (id, role, name, values, cells = {}) => ({ id, role, carrier: 'Harbor', name, values, cells });
const COMPARISON = {
  line: 'medical',
  documents: [{ id: FILE, name: 'renewal.pdf' }],
  // The board's own order: renewals lead their current plan (F120) — the file printed them the other way.
  plans: [
    plan(12, 'renewal', 'PPO 1000', { plan_type: 'PPO', rate_ee: '540' }, { rate_ee: { d: 0, s: 'to_check' } }),
    plan(11, 'current', 'PPO 1000', { plan_type: 'PPO', rate_ee: '500' }, { rate_ee: { d: 0 } }),
    plan(13, 'alternate', 'HMO 2000', { plan_type: 'HMO' }),
  ],
};
const TABLE = {
  document: FILE,
  line: 'medical',
  line_label: 'Medical',
  label: '2027 Renewal',
  where: { page: 3 },
  page_label: '1',
  columns: [
    { col: 0, plan: 11, head: 'PPO 1000' },
    { col: 1, plan: 12, head: 'PPO 1000' },
  ],
  left_out: 0,
  rows: [
    { label: 'Plan type', keys: ['plan_type'] },
    { label: 'Deductible (single / family)', keys: ['deductible_single', 'deductible_family'] },
    { label: 'Chiropractic visits', keys: [], printed: ['20 a year', '25 a year'] },
    { label: 'Employee only', keys: ['rate_ee'] },
  ],
};

describe('F42 E42 a scanned quote as printed', () => {
  const model = buildAsQuoted({ table: TABLE, comparisons: [COMPARISON], meta: META });

  it("keeps the file's column order and printed rows, not the board's", () => {
    const shape = gridShape(model);
    expect(shape.cols).toEqual(['11', '12']);
    expect(shape.rows).toEqual(['plan_type', 'deductible_single', 'deductible_family', `${PRINTED}2`, 'rate_ee']);
    expect(model.sections[0].label).toBe('As printed on page 1 (PDF page 3)');
    expect(model.sections[0].rows[1]).toMatchObject({ label: 'Deductible (single / family)', sub: 'Deductible (Single)' });
  });

  it('shows live values on mapped rows and the printed text, never a value, on a row that fills no field', () => {
    expect(cellAt(model, 'rate_ee', 12)).toMatchObject({ raw: '540', here: true, applies: true, potential: true });
    const chiro = cellAt(model, `${PRINTED}2`, 12);
    expect(chiro).toMatchObject({ raw: '', printed: '25 a year', applies: false, potential: false });
    expect(model.issues.get(12)).toBe(1);
  });

  it('leaves out a plan whose line is not loaded, and says where a sheet prints the table', () => {
    const wider = { ...TABLE, columns: [...TABLE.columns, { col: 2, plan: 99 }] };
    const lone = buildAsQuoted({ table: wider, comparisons: [COMPARISON], meta: META });
    expect(lone.plans.map((p) => p.id)).toEqual([11, 12]);
    expect(printedWhere({ where: { sheet: 'Medical' } })).toBe('sheet “Medical”');
    expect(printedWhere({ where: { page: 2 }, page_label: '' })).toBe('page 2');
    expect(buildAsQuoted({ table: null, comparisons: [COMPARISON], meta: META }).sections).toEqual([]);
  });

  it('finds a printed row by its label', () => {
    const found = gridFind(model, model, findTerms('chiropractic', carrierForms([])), new Map());
    expect(found.hits.map((hit) => hit.key)).toEqual([`${PRINTED}2|@label`]);
  });
});
