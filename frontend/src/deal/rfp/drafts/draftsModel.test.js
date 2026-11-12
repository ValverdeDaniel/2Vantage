import { describe, expect, it } from 'vitest';
import { copyText, draftsSummary, offersMarketed, optimisticSent, routeWords, toWords } from './draftsModel';

const drafts = {
  route: 'direct',
  total: 2,
  sent_count: 0,
  any_sent: false,
  rows: [
    { key: 'aetna', to: '', cc: 'quotes@example.test', subject: 'RFP: Example Co.', body: 'Hi,', sent: null },
    { key: 'cigna', to: '', cc: '', subject: 'RFP: Example Co.', body: 'Hi,', sent: null },
  ],
};

describe('K57–K66 the Emails card (draftsModel)', () => {
  it('says how many are marked sent, or that there are no drafts', () => {
    expect(draftsSummary(drafts)).toBe('Marked sent 0 of 2');
    expect(draftsSummary({ total: 0 })).toBe('No drafts yet');
  });

  it('words the route and the To line, with the rep and the returns inbox', () => {
    expect(routeWords('direct')).toMatch(/^One draft per carrier/);
    expect(routeWords('warner')).toMatch(/Warner Pacific’s quoting inbox/);
    expect(toWords(drafts.rows[0])).toBe('your rep · cc quotes@example.test');
    expect(toWords({ to: 'FLQuoting@WarnerPacific.com', cc: '' })).toBe('FLQuoting@WarnerPacific.com');
  });

  it('copies the subject and the body together (K62)', () => {
    expect(copyText(drafts.rows[0])).toBe('Subject: RFP: Example Co.\n\nHi,');
  });

  it('shows a tick at once and counts it', () => {
    const after = optimisticSent(drafts, 'aetna', true);
    expect(after.sent_count).toBe(1);
    expect(optimisticSent(after, 'aetna', false).sent_count).toBe(0);
  });

  it('offers Mark as marketed once something went out and the deal is not marked (K33, OQ52)', () => {
    expect(offersMarketed({ any_sent: true }, null)).toBe(true);
    expect(offersMarketed({ any_sent: true }, '2026-11-11T10:00:00Z')).toBe(false);
    expect(offersMarketed({ any_sent: false }, null)).toBe(false);
  });
});
