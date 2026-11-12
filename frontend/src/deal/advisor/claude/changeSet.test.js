import { describe, expect, it } from 'vitest';
import {
  applyBody,
  asProposed,
  byLine,
  headChip,
  initialPicks,
  linkText,
  movedPct,
  planItems,
  printedRows,
  rowsFor,
  togglePick,
} from './changeSet';

const changeSet = {
  items: [
    { id: 'i1', op: 'create_plan', role: 'current', line: 'medical', name: 'BlueOptions PPO 2500', tick: true,
      values: [{ key: 'rate_ee', new: '702.4' }], unmapped: [{ label: 'Chiro', printed: '20 a year' }] },
    { id: 'i2', op: 'create_plan', role: 'renewal', line: 'medical', name: 'BlueOptions PPO 2500', tick: true,
      renews: { item: 'i1' }, values: [{ key: 'rate_ee', new: '761.4' }, { key: 'pcp_copay', new: '30' }] },
    { id: 'i3', op: 'summary_counts', line: 'medical', tick: false, counts: { EE: 18 } },
  ],
};

describe('the quote change set (D28, D31)', () => {
  it('keeps plans in reading order and opens with the server ticks', () => {
    expect(planItems(changeSet).map((item) => item.id)).toEqual(['i1', 'i2']);
    expect([...initialPicks(changeSet)]).toEqual(['i1', 'i2']);
    expect(byLine(planItems(changeSet))).toHaveLength(1);
  });

  it('shows only the fields some plan prints, in the line groups order', () => {
    const groups = [
      { key: 'copay', label: 'Copays', fields: ['pcp_copay', 'er_copay'] },
      { key: 'rates', label: 'Rates', fields: ['rate_ee', 'rate_es'] },
    ];
    const sections = rowsFor(planItems(changeSet), groups, [{ key: 'rate_ee', label: 'Rate — EE' }]);
    expect(sections.map((s) => s.rows.map((r) => r.key))).toEqual([['pcp_copay'], ['rate_ee']]);
    expect(sections[1].rows[0].cells.i1.new).toBe('702.4');
    expect(sections[0].rows[0].cells.i1).toBeNull();
    expect(printedRows(planItems(changeSet))).toEqual([{ label: 'Chiro', cells: { i1: '20 a year' } }]);
  });

  it('says what each column would become and what it renews', () => {
    expect(headChip(changeSet.items[0]).text).toBe('NEW · Current');
    expect(headChip({ op: 'pick_current' }).text).toBe('Which current plan?');
    expect(linkText(changeSet.items[1], changeSet.items)).toBe('Renews BlueOptions PPO 2500 (in this read)');
  });

  it('moves a number by its signed percentage, the old card’s rule', () => {
    expect(movedPct('702.40', '761.40')).toBe('+8.4%');
    expect(movedPct('100', '100')).toBe('');
    expect(movedPct('', '5')).toBe('');
  });
});

describe('using the read (D28, D31, D72, D117)', () => {
  it('uses the read as proposed until a tick changes, then applies what is ticked', () => {
    const picks = initialPicks(changeSet);
    expect(asProposed(picks, changeSet)).toBe(true);
    expect(applyBody(picks, changeSet)).toEqual({});
    const withCounts = togglePick(picks, 'i3');
    expect(asProposed(withCounts, changeSet)).toBe(false);
    expect(applyBody(withCounts, changeSet)).toEqual({ select: ['i1', 'i2', 'i3'], picks: {} });
  });

  it('ticks a plan with its value, and sends where a "Which current plan?" item goes', () => {
    const picks = togglePick(new Set(), 'i9:rate_ee', 'i9');
    expect([...picks]).toEqual(['i9:rate_ee', 'i9']);
    const placed = { items: [{ id: 'i9', op: 'pick_current', tick: false }] };
    expect(applyBody(picks, placed, { i9: 'new' })).toEqual({ select: ['i9:rate_ee', 'i9'], picks: { i9: 'new' } });
  });
});
