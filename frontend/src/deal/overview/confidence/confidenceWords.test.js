import { describe, expect, it } from 'vitest';
import {
  confirmQuestion,
  docMeta,
  ignoreCount,
  markToast,
  markedMeta,
  recheckBlocked,
  recheckResult,
  rowPath,
} from './confidenceWords';

describe('the data confidence words (M83–M92)', () => {
  it('M87: a file reads its values and confirmations; Ignore takes the warnings not flagged', () => {
    const doc = { values: 12, confirmed: 3, to_review: 4, check: 1 };
    expect(docMeta(doc)).toBe('12 values · 3 confirmed');
    expect(docMeta({ values: 1, confirmed: 0 })).toBe('1 value · 0 confirmed');
    expect(ignoreCount(doc)).toBe(3);
    expect(ignoreCount({ to_review: 1, check: 2 })).toBe(0);
  });

  it('M88: Confirm all asks about the values not yet confirmed, then says what it did', () => {
    expect(confirmQuestion({ values: 12, confirmed: 3 })).toBe('Confirm 9 values from this file?');
    expect(markToast('approve', 9, 'quote.pdf')).toBe('Confirmed 9 values');
    expect(markToast('approve', 0, 'quote.pdf')).toBe('Nothing to confirm on quote.pdf');
    expect(markToast('ignore', 3, 'quote.pdf')).toBe('3 values ignored on quote.pdf');
    expect(markToast('check', 1)).toBe('1 value flagged as needing checking');
    expect(markToast('clear', 0)).toBe('Nothing to undo');
  });

  it('M90: a marked row says who, when and from which file, and opens where its value lives', () => {
    const row = { by: 'Dana Example', at: '2026-11-12T15:00:00Z', doc: { name: 'quote.pdf' }, tab: 'advisor' };
    expect(markedMeta(row)).toMatch(/^Dana Example · .+ · quote\.pdf$/);
    expect(markedMeta({ by: '', at: null, doc: null })).toBe('');
    expect(rowPath(7, row)).toBe('/deals/7/advisor');
    expect(rowPath(7, { tab: 'questionnaire', form: 'fl_blue_51' })).toBe('/deals/7/questionnaire?form=fl_blue_51');
  });

  it('M92: the re-read reads its result, and says why it cannot start', () => {
    const last = { status: 'done', counts: { checked: 11, agreed: 3, differ: 7, not_found: 1 }, at: null };
    expect(recheckResult(last)).toEqual({
      head: 'Re-read 11 scanned values — ',
      agreed: '3 agreed',
      differ: '7 disagree',
      notFound: '1 not found',
      at: '',
    });
    expect(recheckResult({ ...last, status: 'running' })).toBeNull();
    expect(recheckResult(null)).toBeNull();
    expect(recheckBlocked({ claude: false, values: 4 })).toMatch(/no ANTHROPIC_API_KEY/);
    expect(recheckBlocked({ claude: true, values: 0 })).toMatch(/nothing to re-read/);
    expect(recheckBlocked({ claude: true, values: 4, running: true })).toMatch(/busy/);
    expect(recheckBlocked({ claude: true, values: 4, running: false })).toBe('');
  });
});
