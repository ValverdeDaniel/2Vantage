import { describe, expect, it } from 'vitest';
import { firstPicks, recheckSource, recheckTitle, rowMeta, sections } from './recheckWords';

const value = (key, old, nu, extra = {}) => ({ key, label: key, old, new: nu, page: 1, confidence: 'high', note: '', ...extra });
const CHANGES = {
  documents: [7],
  counts: { approvals: 2, fixes: 1, unverified: 1 },
  items: [
    { id: 'i1', op: 'confirm', plan: 41, carrier: 'Cigna', name: 'OAP', tick: true, values: [value('pcp_copay', '35', '35')] },
    { id: 'i2', op: 'confirm', plan: 42, carrier: 'UHC', name: 'Choice', tick: true, values: [value('er_copay', '250', '250')] },
    { id: 'i3', op: 'set_values', plan: 41, carrier: 'Cigna', name: 'OAP', tick: false, values: [value('rate_ee', '512', '521', { confidence: 'low' })] },
  ],
};

describe('the re-check card (D93, E77)', () => {
  it('ticks what Claude proposes, an unsure fix left unticked', () => {
    expect([...firstPicks(CHANGES)]).toEqual(['i1', 'i2']);
  });

  it('groups agreements and fixes by plan, in the old words', () => {
    const [approve, fix] = sections(CHANGES);
    expect(approve.title).toBe('Claude agrees — approve these 2');
    expect(approve.groups.map((group) => group.label)).toEqual(['Cigna OAP', 'UHC Choice']);
    expect(fix.title).toBe('Claude proposes a fix');
    expect(recheckTitle(CHANGES)).toBe('Claude re-checked the flags: 2 look right, 1 needs a fix');
  });

  it('names the one file and the values read, and how sure Claude was', () => {
    expect(recheckSource(CHANGES, () => 'Cigna SBC')).toBe('Re-read 4 flagged values against their pages in “Cigna SBC”');
    expect(rowMeta(CHANGES.items[2].values[0])).toBe('p.1 · unsure');
  });
});
