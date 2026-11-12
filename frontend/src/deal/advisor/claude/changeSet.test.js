import { describe, expect, it } from 'vitest';
import { byLine, headChip, initialPicks, linkText, movedPct, planItems, printedRows, rowsFor } from './changeSet';

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
