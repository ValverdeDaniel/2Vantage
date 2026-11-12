import { describe, expect, it } from 'vitest';
import { boardColumns, exportKeys, sections, shownKeys } from './boardColumns';
import { buildBoard, countLine, networkType, numberOf, transposeState } from './boardModel';
import { complianceFailures, complianceText, complianceTitle, planChips, supersededIds } from './chips';

// The parts of /api/meta/ the board reads (quotes/board_presets.py and quotes/fields.py), for one medical line.
const meta = {
  plans: {
    fields: [
      { key: 'network', label: 'Network', type: 'text' },
      { key: 'deductible_single', label: 'Deductible (Single)', type: 'amount' },
      { key: 'oop_max_single', label: 'OOP Max (Single)', type: 'amount' },
      { key: 'rate_ee', label: 'Rate — EE', type: 'rate' },
    ],
  },
  board: {
    default_preset: 'primary',
    columns: {
      medical: {
        primary: ['total', 'delta', 'deductible_single', 'oop_max_single', 'network_type', 'flags'],
        rates: ['total', 'delta', 'rate_ee'],
        all: ['total', 'delta', 'network', 'deductible_single', 'oop_max_single', 'rate_ee', 'flags'],
      },
    },
    pinned: [
      { key: 'star', label: '★', sort: true },
      { key: 'carrier', label: 'Plan', sort: true },
    ],
    derived: [
      { key: 'flags', label: 'Flags', sort: false, group: 'info', at: 'start' },
      { key: 'network_type', label: 'Network / type', sort: true, group: 'info', at: 'start' },
      { key: 'total', label: 'Monthly total', sort: true, group: 'cost', at: 'end' },
      { key: 'delta', label: 'Δ vs current', sort: true, group: 'cost', at: 'end' },
    ],
    group_labels: { cost: 'Cost Summary' },
    compliance: [
      { key: 'minimum_value', short: 'MV', label: 'minimum value', why: 'MV why.' },
      { key: 'part_d_creditable', short: 'Part D', label: 'Medicare Part D creditable coverage', why: 'D why.' },
    ],
  },
};
const groups = [
  { key: 'info', label: 'Plan info', fields: ['network'] },
  { key: 'deduct', label: 'Deductibles & maximums', fields: ['deductible_single', 'oop_max_single'] },
  { key: 'rates', label: 'Monthly rates', fields: ['rate_ee'] },
];
const p = (id, role, extra = {}) => ({ id, role, carrier: 'Aetna', name: `Plan ${id}`, values: {}, base_ids: [], ...extra });

describe('F31 F41 the columns', () => {
  it('pins ☐, ★ and Plan before the preset the server lists for the line', () => {
    expect(boardColumns(meta, 'medical', 'rates', 'proposal').map((c) => c.key)).toEqual([
      'select', 'star', 'carrier', 'total', 'delta', 'rate_ee',
    ]);
    const [, , plan, total] = boardColumns(meta, 'medical', 'rates', 'proposal');
    expect(plan).toMatchObject({ kind: 'plan', label: 'Plan', sortable: true });
    expect(total).toMatchObject({ kind: 'derived', label: 'Monthly total', numeric: true });
  });

  it('F32 keeps the sorted column on screen when the preset hides it, before Flags', () => {
    expect(shownKeys(meta, 'medical', 'primary', 'rate_ee')).toEqual([
      'total', 'delta', 'deductible_single', 'oop_max_single', 'network_type', 'rate_ee', 'flags',
    ]);
    expect(shownKeys(meta, 'medical', 'primary', 'closest')).not.toContain('closest');
    expect(shownKeys(meta, 'medical', 'unknown', 'proposal')).toEqual(meta.board.columns.medical.primary);
  });

  it('F35 transposed, places the preset in the line groups with the derived rows where they stand', () => {
    const keys = shownKeys(meta, 'medical', 'primary', 'proposal');
    expect(sections(meta, groups, keys)).toEqual([
      { group: 'info', label: 'Plan info', keys: ['flags', 'network_type'] },
      { group: 'deduct', label: 'Deductibles & maximums', keys: ['deductible_single', 'oop_max_single'] },
      { group: 'cost', label: 'Cost Summary', keys: ['total', 'delta'] },
    ]);
  });

  it('F93 exports the columns drawn, without the screen-only ones', () => {
    const columns = boardColumns(meta, 'medical', 'primary', 'proposal');
    expect(exportKeys(columns)).toEqual(['total', 'delta', 'deductible_single', 'oop_max_single', 'network_type', 'flags']);
    const list = sections(meta, groups, shownKeys(meta, 'medical', 'primary', 'proposal'));
    expect(exportKeys(columns, list)).toEqual(['flags', 'network_type', 'deductible_single', 'oop_max_single', 'total', 'delta']);
  });
});

describe('F32 the sort', () => {
  const comparison = {
    plans: [
      p(1, 'current', { premium: { monthly: 100 } }),
      p(2, 'alternate', { premium: { monthly: 300 }, values: { deductible_single: '1500' }, closeness: 0.4 }),
      p(3, 'alternate', { premium: { monthly: null }, values: { deductible_single: '500' }, closeness: 0.1 }),
      p(4, 'renewal', { premium: { monthly: 200 }, values: { deductible_single: '$3,300' }, closeness: null }),
    ],
  };
  const order = (sort) => buildBoard({ comparison, meta, line: 'medical', preset: 'primary', sort }).sorted.map((x) => x.id);

  it('Proposal order is the server order, and never moves on a value', () => {
    expect(order({ key: 'proposal', dir: 1 })).toEqual([2, 3, 4]);
  });

  it('sorts by the server figures and by values, blanks last', () => {
    expect(order({ key: 'total', dir: 1 })).toEqual([4, 2, 3]);
    expect(order({ key: 'total', dir: -1 })).toEqual([2, 4, 3]);
    expect(order({ key: 'deductible_single', dir: 1 })).toEqual([3, 2, 4]);
    expect(order({ key: 'closest', dir: 1 })).toEqual([3, 2, 4]);
  });

  it('reads numbers and the network words', () => {
    expect(numberOf('$3,300')).toBe(3300);
    expect(numberOf('$25 – $135')).toBeNull();
    expect(networkType({ values: { network: 'Open Access', plan_type: 'HDHP' } })).toBe('Open Access · HDHP');
  });
});

describe('F9 the count line', () => {
  const quotes = [p(2, 'alternate', { starred: true }), p(3, 'alternate')];
  it('counts this line only and names the current package total', () => {
    const packages = [{ key: 'current', monthly: 18251.4 }];
    expect(countLine({ shown: 2, quotes, currents: [p(1, 'current')], packages })).toBe(
      'Showing 2 of 2 quoted plans · 1 shortlisted · current plan (Aetna) $18,251/mo',
    );
  });

  it('says what several or no current plans mean', () => {
    const two = countLine({ shown: 2, quotes, currents: [p(1, 'current'), p(4, 'current')], packages: [] });
    expect(two).toContain('2 current plans — link each starred quote to the plan it replaces');
    expect(countLine({ shown: 0, quotes: [], currents: [] })).toBe(
      'Showing 0 of 0 quoted plans · no current plan set — Δ% is unavailable',
    );
  });
});

describe('F62 the chips', () => {
  it('numbers CURRENT when the line has several', () => {
    const currents = [p(1, 'current'), p(2, 'current')];
    expect(planChips(currents[1], { currents }).map((c) => c.text)).toEqual(['CURRENT 2']);
    expect(planChips(currents[0], { currents: [currents[0]] }).map((c) => c.text)).toEqual(['CURRENT']);
  });

  it('marks a priced version and the quote it supersedes; a duplicate wears nothing', () => {
    const plans = [
      p(3, 'alternate'),
      p(4, 'alternate', { derived_from: 3, derived: { kind: 'concession', label: '5% off' } }),
      p(5, 'alternate', { derived_from: 3, derived: { kind: 'duplicate' } }),
    ];
    const superseded = supersededIds(plans);
    expect(planChips(plans[0], { supersededIds: superseded }).map((c) => c.text)).toEqual(['superseded']);
    expect(planChips(plans[1], { supersededIds: superseded }).map((c) => c.text)).toEqual(['5% OFF']);
    expect(planChips(plans[2], { supersededIds: superseded })).toEqual([]);
  });

  it('D-051 names the compliance tests the carrier says it fails, from meta', () => {
    const failing = complianceFailures({ facts: { compliance: ['part_d_creditable', 'minimum_value'] } }, meta.board.compliance);
    expect(complianceText(failing)).toBe('⚠ MV · Part D');
    expect(complianceTitle(failing)).toBe(
      'The carrier says this plan does not meet minimum value and Medicare Part D creditable coverage. MV why. D why.',
    );
    expect(complianceText(complianceFailures({ facts: { compliance: [] } }, meta.board.compliance))).toBe('');
  });
});

describe('F34 the transpose limit', () => {
  it('flips up to the limit and keeps the board in rows above it, whatever was chosen', () => {
    expect(transposeState(60, 60, 'cols')).toEqual({ blocked: false, shown: 'cols' });
    expect(transposeState(61, 60, 'cols')).toEqual({ blocked: true, shown: 'rows' });
    expect(transposeState(3, 60, 'rows')).toEqual({ blocked: false, shown: 'rows' });
  });
});
