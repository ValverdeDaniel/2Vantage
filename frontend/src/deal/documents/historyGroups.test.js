import { describe, expect, it } from 'vitest';
import { groupRows, groupSummary, kindOf, rowIcon } from './historyGroups';

const row = (id, at, actor, extra = {}) => ({
  id,
  at,
  actor,
  actor_kind: 'user',
  area: 'quotes',
  action: 'updated',
  summary: 'Edited 1 plan value',
  count: 1,
  ...extra,
});

describe('the Change history (E73, E74)', () => {
  it('E73 groups one person’s rows within 30 minutes, newest first', () => {
    const rows = [
      row(5, '2026-11-11T15:40:00Z', 'Dana'),
      row(4, '2026-11-11T15:20:00Z', 'Dana', { action: 'marked', summary: 'Approved 3 plan values', count: 3 }),
      row(3, '2026-11-11T15:12:00Z', 'Dana', { area: 'documents', action: 'created', summary: 'Uploaded a Quote file' }),
      row(2, '2026-11-11T14:59:00Z', 'Omar'),
      row(1, '2026-11-11T14:00:00Z', 'Omar'),
    ];
    const groups = groupRows(rows);
    expect(groups.map((g) => [g.actor, g.items.map((r) => r.id)])).toEqual([
      ['Dana', [5, 4, 3]],
      ['Omar', [2]],
      ['Omar', [1]],
    ]);
    expect(groups[0].start).toBe('2026-11-11T15:12:00Z');
    expect(groupSummary(groups[0])).toBe('1 change · 1 file action · 3 values reviewed');
  });

  it('E74 tells reviews, file actions and other changes apart', () => {
    expect(kindOf(row(1, '', 'Dana', { action: 'marked' }))).toBe('review');
    expect(kindOf(row(1, '', 'Dana', { area: 'documents' }))).toBe('file');
    expect(rowIcon(row(1, '', 'Dana', { area: 'documents', action: 'created' }))).toBe('⤓');
    expect(rowIcon(row(1, '', 'Dana', { action: 'marked' }))).toBe('✓');
    expect(groupSummary({ items: [] })).toBe('0 events');
  });
});
