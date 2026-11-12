import { describe, expect, it } from 'vitest';
import {
  bundleScopeIds,
  draftBody,
  draftFromVersion,
  emptyDraft,
  familyAllowed,
  inheritLabel,
  openDraft,
  pricedChipText,
  requirementDetail,
} from './pricedKinds';
import { formulaLabel, stackColumns } from './stack';

const priced = {
  families: [
    { key: 'concession', label: 'Concession', glyph: '%' },
    { key: 'bundle', label: 'Bundling discount', glyph: '⊕' },
    { key: 'holiday', label: 'Premium holiday', glyph: '$' },
    { key: 'duplicate', label: 'Duplicate', glyph: '⧉' },
  ],
  ops: [
    { key: 'pct_off', label: '% off' },
    { key: 'flat_off', label: '$ off' },
  ],
  pct_ops: ['pct_off', 'pct_up'],
  quoted: 'group_premium_monthly',
  words: { one_plan_credit: 'A dollar credit belongs to one plan — pick one.' },
};

const p = (id, extra = {}) => ({ id, role: 'alternate', carrier: 'Cigna', name: `Plan ${id}`, sold: false, ...extra });

describe('F76–F81 the priced-version draft', () => {
  it('opens on a premium holiday for the in-force plan and a concession for a quote', () => {
    expect(openDraft(p(1, { role: 'current' }), false).family).toBe('holiday');
    expect(openDraft(p(2), true)).toMatchObject({ family: 'concession', planIds: [2], anchorId: 2, expanded: true });
    expect(familyAllowed('concession', { role: 'current' })).toBe(false);
    expect(familyAllowed('duplicate', { role: 'current' })).toBe(true);
  });

  it('a bundle covers every quote of the carrier that can take one, else the anchor alone', () => {
    const plans = [
      p(1, { role: 'current' }),
      p(2),
      p(3, { sold: true }),
      p(4, { bundling: 'included' }),
      p(5, { derived_from: 2, derived: { kind: 'concession' } }),
      p(6, { derived_from: 2, derived: { kind: 'duplicate' } }),
      p(7, { carrier: 'UHC' }),
    ];
    expect(bundleScopeIds(plans, plans[1])).toEqual([2, 6]);
    expect(bundleScopeIds(plans, plans[6])).toEqual([7]);
    expect(bundleScopeIds([p(9, { sold: true })], p(9, { sold: true }))).toEqual([9]);
  });

  it('builds one request for the row, the composer and the dry run, and says what is missing', () => {
    const draft = emptyDraft({
      planIds: [2],
      anchorId: 2,
      allValue: '5',
      each: { rate_ee: 'keep', rate_es: { op: 'set', value: '' } },
    });
    expect(draftBody(draft).body).toEqual({
      kind: 'concession',
      note: '',
      name: '',
      all: { op: 'pct_off', value: '5' },
      each: { rate_ee: 'keep' },
      plan_ids: [2],
    });
    expect(draftBody(emptyDraft({ planIds: [2] })).error).toMatch(/Set a change for all rates/);
    const holiday = emptyDraft({ family: 'holiday', planIds: [2, 3], credit: '3000' });
    expect(draftBody(holiday, priced.words).error).toBe(priced.words.one_plan_credit);
    expect(draftBody({ ...holiday, credit: '', months: '1' }).body.credit).toEqual({ months: '1' });
    const bundle = emptyDraft({
      family: 'bundle',
      planIds: [2],
      carrier: 'Cigna',
      parts: {
        dental: { op: 'pct_off', value: '2', plan_id: 9 },
        vision: { op: 'pct_off', value: '1' },
        std: { value: '' },
      },
    });
    expect(draftBody(bundle).body.parts).toEqual([
      { line: 'dental', op: 'pct_off', value: '2', plan_id: 9 },
      { line: 'vision', op: 'pct_off', value: '1', carrier: 'Cigna' },
    ]);
    const edit = emptyDraft({ editId: 12, planIds: [2], allValue: '6' });
    expect(draftBody(edit).body).not.toHaveProperty('plan_ids');
  });

  it('✎ reopens a version from its record, locked to its kind', () => {
    const version = p(12, {
      derived_from: 2,
      derived: {
        kind: 'concession',
        all: { op: 'pct_off', value: 5 },
        each: { rate_ee: 'keep', rate_fam: { op: 'set', value: 1400 } },
        note: 'per the rep',
      },
    });
    expect(draftFromVersion(version)).toMatchObject({
      family: 'concession',
      editId: 12,
      anchorId: 2,
      planIds: [2],
      allValue: '5',
      each: { rate_ee: 'keep', rate_fam: { op: 'set', value: '1400' } },
      note: 'per the rep',
    });
  });

  it('words an override, a chip and what a bundle needs sold', () => {
    const draft = emptyDraft({ allOp: 'flat_off', allValue: '10' });
    expect(inheritLabel(draft, 'rate_ee', priced)).toBe('as all ($ off 10)');
    expect(inheritLabel(draft, 'group_premium_monthly', priced)).toBe(''); // a dollar amount never reaches it
    expect(pricedChipText(priced, { kind: 'bundle', label: '2% bundled (Dental)' })).toBe('⊕ 2% BUNDLED (DENTAL)');
    const derived = {
      kind: 'bundle',
      parts: [{ plan_label: 'Cigna Dental PPO' }, { carrier: 'Cigna', line: 'vision' }],
    };
    expect(requirementDetail(derived, (key) => ({ vision: 'Vision' })[key])).toBe(
      'Cigna Dental PPO + any Cigna vision',
    );
  });

  it('a draft draws a blue and a draft column right of each plan it prices', () => {
    const kit = {
      priced,
      draft: { family: 'holiday' },
      rowFor: (id) => (id === 2 ? { id: 'draft-2' } : null),
    };
    expect(stackColumns([p(1), p(2), p(3)], kit).map((entry) => entry.key)).toEqual([1, 2, 'formula-2', 'draft-2', 3]);
    expect(stackColumns([p(1)], null).map((entry) => entry.key)).toEqual([1]);
    expect(formulaLabel(kit)).toBe('PREMIUM HOLIDAY · rates unchanged');
  });
});
