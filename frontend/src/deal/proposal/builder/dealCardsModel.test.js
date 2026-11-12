import { describe, expect, it } from 'vitest';
import {
  blockScope,
  everyBlock,
  outputSummary,
  pageMissing,
  pageStatus,
  pagesSummary,
  pinnedBlock,
  savedPeriods,
  savedSteps,
  summaryBlocks,
  summaryWords,
  takesPin,
  toggledBlock,
  toggledHidden,
} from './dealCardsModel';

const meta = { layouts: [{ key: 'by_carrier', label: 'A page per carrier' }] };

describe('the deal cards (J38–J45, J63–J67)', () => {
  it('J38 reads the layout in the card summary', () => {
    expect(outputSummary({ layout: 'by_carrier' }, meta)).toBe('Presentation · a page per carrier');
  });

  it('J42 says whether each page prints, and why not', () => {
    const ledger = [
      { key: 'agenda', switchable: true, ready: null, why: 'prints with three or more sections' },
      { key: 'experience', switchable: true, ready: false, why: 'nothing typed yet' },
      { key: 'overview', switchable: false, ready: true, why: '' },
    ];
    expect(pageStatus(ledger[0], {})).toBe('prints with three or more sections');
    expect(pageStatus(ledger[1], { experience: false })).toBe('switched off');
    expect(pageStatus(ledger[2], {})).toBe('prints');
    expect(pageMissing(ledger[1], {})).toBe(true);
    expect(pageMissing(ledger[1], { experience: false })).toBe(false);
    expect(pagesSummary(ledger, { agenda: false })).toBe('1 of 2 pages on');
  });

  it('J64 builds every edit on the standard set until something is picked', () => {
    const summary = { on: true, picked: [], standard: [{ key: 'total_current' }, { key: 'recommended' }] };
    expect(summaryBlocks(summary)).toEqual(summary.standard);
    expect(summaryWords(summary)).toBe('The standard set');
    expect(toggledBlock(summaryBlocks(summary), 'total_current')).toEqual([{ key: 'recommended' }]);
    expect(toggledBlock([{ key: 'recommended' }], 'spread')).toEqual([{ key: 'recommended' }, { key: 'spread' }]);
    expect(pinnedBlock([{ key: 'recommended' }], 'recommended', 'dental')).toEqual([
      { key: 'recommended', line: 'dental' },
    ]);
    expect(pinnedBlock([{ key: 'recommended', line: 'dental' }], 'recommended', '')).toEqual([{ key: 'recommended' }]);
    const catalog = [{ key: 'recommended' }, { key: 'spread' }];
    expect(everyBlock([{ key: 'recommended', line: 'dental' }], catalog)).toEqual([
      { key: 'recommended', line: 'dental' },
      { key: 'spread' },
    ]);
    expect(summaryWords({ on: false, picked: [] })).toBe('Not shown');
    expect(summaryWords({ on: true, picked: [{ key: 'spread' }] })).toBe('1 figure');
  });

  it('J64 offers a line pin only on a per-line block that belongs to no one line', () => {
    const label = (line) => ({ medical: 'Medical' })[line];
    expect(blockScope({ scope: 'deal' }, label)).toBe('whole deal');
    expect(blockScope({ scope: 'line', line: 'medical' }, label)).toBe('Medical only');
    expect(blockScope({ scope: 'line' }, label)).toBe('per line');
    expect(takesPin({ scope: 'line' })).toBe(true);
    expect(takesPin({ scope: 'line', line: 'medical' })).toBe(false);
  });

  it('J63 J45 J67 keep only what is worth saving', () => {
    expect(toggledHidden(['n:vsp'], 'cigna')).toEqual(['cigna', 'n:vsp']);
    expect(toggledHidden(['cigna'], 'cigna')).toEqual([]);
    expect(savedSteps([{ text: ' ' }, { text: 'Sign', date: '' }])).toEqual([{ text: 'Sign', date: '' }]);
    expect(savedPeriods([{ period: '' }, { period: '2025', premium: 1 }])).toEqual([{ period: '2025', premium: 1 }]);
  });
});
