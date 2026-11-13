import { describe, expect, it } from 'vitest';
import { waitingView } from './waitingView';

const next = (label, more = {}) => ({ key: 'step', label, link: '/deals/7/intake', state: 'open', severity: 'warn',
  ...more }); // prettier-ignore

describe("the Overview's Waiting banner (M33, M34, I119)", () => {
  it('M34 draws nothing on a lost deal, which the journey answers with no waiting', () => {
    expect(waitingView({ waiting: null, next_step: { key: 'lost', label: 'Deal lost', state: 'lost' } })).toBeNull();
    expect(waitingView(undefined)).toBeNull();
  });

  it('M33 waiting on the client: its words, how long, with them, and the next step when it differs', () => {
    const view = waitingView({
      waiting: { state: 'waiting', label: 'Waiting on the client for the census', owner: 'client', days: 1,
        severity: 'info' }, // prettier-ignore
      next_step: next('Mark as marketed'),
    });
    expect(view).toEqual({
      done: false,
      side: 'them',
      label: 'Waiting on the client for the census',
      detail: 'Waiting 1 day so far.',
      next: 'Mark as marketed',
      link: '/deals/7/intake',
      severity: 'info',
    });
  });

  it('M33 a wait with no start day has no detail, and a next step with the same words is not repeated', () => {
    const view = waitingView({
      waiting: { state: 'waiting', label: 'Waiting on carrier quotes', owner: 'carrier', days: null, severity: 'warn' },
      next_step: next('Waiting on carrier quotes'),
    });
    expect([view.detail, view.next, view.severity]).toEqual(['', '', 'warn']);
  });

  it("M33 with us: the next step is the headline, the ball in our court the detail, Go ▸ opens the step's link", () => {
    const view = waitingView({
      waiting: { state: 'with_us', label: 'The ball is in our court', next: 'Complete intake' },
      next_step: next('Complete intake', { severity: 'error', link: '/deals/7/intake?view=review' }),
    });
    expect(view).toEqual({
      done: false,
      side: 'us',
      label: 'Complete intake',
      detail: 'The ball is in our court.',
      next: '',
      link: '/deals/7/intake?view=review',
      severity: 'error',
    });
  });

  it('M33 nothing left reads Status · the sale or Complete, with no Go ▸', () => {
    const sold = waitingView({
      waiting: { state: 'with_us', label: 'The ball is in our court', next: 'Sold' },
      next_step: next('Sold', { state: 'done', severity: 'done' }),
    });
    expect([sold.done, sold.label, sold.link, sold.side]).toEqual([true, 'Sold', null, null]);
    const none = waitingView({ waiting: { state: 'with_us', label: 'The ball is in our court' }, next_step: null });
    expect([none.label, none.detail, none.severity]).toEqual(['Complete', 'Nothing outstanding on this deal.', 'done']);
  });
});
