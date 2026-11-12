import { describe, expect, it } from 'vitest';
import { rankLabel, rankLandedText, rankScope, rankTitle, rankToast } from './rankWords';

const BOARD = { line: 'medical', shown_ids: [4, 5, 6], total: 14 };

describe('⚖ Rank plans (D6, F111, OQ44)', () => {
  it('ranks the board’s line, and only the plans a filtered board shows', () => {
    expect(rankScope(BOARD)).toEqual({ line: 'medical', planIds: [4, 5, 6], filtered: true });
    expect(rankScope({ ...BOARD, total: 3 })).toEqual({ line: 'medical', planIds: null, filtered: false });
    expect(rankScope(null, 'dental')).toEqual({ line: 'dental', planIds: null, filtered: false });
  });

  it('says what it ranks, or that it is ranking', () => {
    expect(rankLabel(rankScope(BOARD), false)).toBe('⚖ Rank filtered (3)');
    expect(rankLabel(rankScope(null, 'medical'), false)).toBe('⚖ Rank plans');
    expect(rankLabel(rankScope(BOARD), true)).toBe('Ranking…');
  });

  it('says "Add client guidance first" without guidance, and the lock first when locked', () => {
    const scope = rankScope(BOARD);
    expect(rankTitle({ locked: false, guidance: '', scope })).toBe('Add client guidance first');
    expect(rankTitle({ locked: true, guidance: '', scope })).toMatch(/locked from Claude/);
    expect(rankTitle({ locked: false, guidance: 'HSA', scope })).toMatch(/stars outside the filter stay/);
    expect(rankTitle({ locked: false, guidance: 'HSA', scope: rankScope(null) })).toMatch(/Open a line/);
  });

  it('tells how a rank ended (D36)', () => {
    expect(rankLandedText({ summary: 'starred 6 Medical plans' })).toBe('★ Claude ranked the plans — starred 6 Medical plans');
    expect(rankToast({ status: 'failed', error: 'Add client guidance first.' })).toEqual({ tone: 'error', text: 'Add client guidance first.' });
    expect(rankToast({ status: 'done', landed: { plan_ids: [1], summary: 'starred 1 Medical plan' } }).text).toBe(
      'Shortlist updated — starred 1 Medical plan',
    );
    expect(rankToast({ status: 'done', landed: { plan_ids: [] } })).toBeNull();
  });
});
