import { describe, expect, it } from 'vitest';
import { askable, trayState } from './trayAsk';

const tray = {
  asks_closed: null,
  items: [{ id: 7, ref: 'intake:fein' }],
  out: { 'intake:dba': '2026-10-20T14:00:00Z' },
};

describe('B12 L54 an item says where it stands with the tray', () => {
  it('in the tray, asked on a link they have, or not asked', () => {
    expect(trayState(tray, 'intake:fein')).toEqual({ state: 'in_tray', draftId: 7 });
    expect(trayState(tray, 'intake:dba')).toEqual({ state: 'asked', at: '2026-10-20T14:00:00Z' });
    expect(trayState(tray, 'intake:website')).toEqual({ state: 'ask' });
  });
  it('asks nothing on a deal that may no longer ask its client', () => {
    expect(trayState({ ...tray, asks_closed: 'This deal is lost.' }, 'intake:website')).toEqual({ state: 'closed' });
  });
  it('"＋ Ask N" takes only what is neither in the tray nor out', () => {
    expect(askable(tray, ['intake:fein', 'intake:dba', 'intake:website', 'doc:claims'])).toEqual([
      'intake:website',
      'doc:claims',
    ]);
  });
});
