import { describe, expect, it } from 'vitest';
import { agoWords, labelIn, linkDetail, linkUrl, pillLabel, runsOutWords, viewOf, waitingCount } from './reviewModel';

const NOW = new Date('2026-11-12T15:00:00Z');

describe('the View row (L1)', () => {
  it('opens the Board unless a built view is asked', () => {
    expect(viewOf(new URLSearchParams(''))).toBe('board');
    expect(viewOf(new URLSearchParams('view=request'))).toBe('request');
    expect(viewOf(new URLSearchParams('view=queue'))).toBe('board');
  });

  it('counts what is to send and to review on the pills', () => {
    expect(pillLabel('request', { to_send: 0 })).toBe('Request');
    expect(pillLabel('request', { to_send: 2 })).toBe('Request · 2 to send');
    expect(pillLabel('queue', { to_review: 3 })).toBe('Review · 3');
    expect(pillLabel('board', {})).toBe('Board');
  });
});

describe('a link, said of the link (L8)', () => {
  it.each([
    [{ state: 'draft' }, 'nobody has this URL yet'],
    [{ state: 'waiting', sent_at: '2026-11-10T15:00:00Z' }, 'sent 2d ago · not opened yet'],
    [{ state: 'opened', opens: 3, last_opened_at: '2026-11-12T12:00:00Z' }, 'this link was opened 3× · last 3h ago'],
    [{ state: 'expired', opened: false }, 'not opened before it expired'],
    [{ state: 'off' }, 'a person turned it off, so it no longer opens'],
    [{ state: 'closed' }, 'its request was closed, so this link no longer opens'],
    [{ state: 'answered', submitted_at: '2026-11-12T14:59:30Z' }, 'sent back just now'],
  ])('%o reads "%s"', (person, words) => {
    expect(linkDetail(person, NOW)).toBe(words);
  });

  it('says how soon a card runs out', () => {
    expect(runsOutWords(0)).toBe('Runs out in under a day');
    expect(runsOutWords(1)).toBe('Runs out in 1 day');
    expect(runsOutWords(2)).toBe('Runs out in 2 days');
  });

  it('reads short times', () => {
    expect(agoWords('2026-11-12T14:48:00Z', NOW)).toBe('12 min ago');
    expect(agoWords('', NOW)).toBe('');
  });
});

describe('the Waiting lane', () => {
  it('counts its requests and who is still answering', () => {
    expect(waitingCount({ lanes: { waiting: [{}, {}] }, in_progress: [{}] })).toBe(3);
    expect(waitingCount(null)).toBe(0);
  });

  it('copies the full URL from the server path, never inventing one', () => {
    expect(linkUrl('/portal/abc', 'http://localhost:4001')).toBe('http://localhost:4001/portal/abc');
    expect(linkUrl(null, 'http://localhost:4001')).toBe('');
  });

  it('reads labels from the vocabulary', () => {
    expect(labelIn([{ key: 'off', label: 'Turned off' }], 'off')).toBe('Turned off');
    expect(labelIn([], 'off')).toBe('off');
  });
});
