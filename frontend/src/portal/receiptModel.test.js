import { describe, expect, it } from 'vitest';
import { followUpWaits, opensOnReceipt, sentWords } from './receiptModel';

describe('the receipt (L99; slice 59)', () => {
  it('opens a submitted link on its receipt, and a link nobody submitted on the form', () => {
    expect(opensOnReceipt({ submitted_at: '2026-11-12T15:04:00Z', follow_ups: [] })).toBe(true);
    expect(opensOnReceipt({ submitted_at: null, follow_ups: [] })).toBe(false);
  });

  it('opens on the form while a follow-up waits for their answer (old D-142)', () => {
    const waiting = { needs_answer: true, answered: false };
    expect(followUpWaits({ follow_ups: [waiting] })).toBe(true);
    expect(opensOnReceipt({ submitted_at: '2026-11-12T15:04:00Z', follow_ups: [waiting] })).toBe(false);
    const answered = { needs_answer: true, answered: true };
    expect(opensOnReceipt({ submitted_at: '2026-11-12T15:04:00Z', follow_ups: [answered] })).toBe(true);
  });

  it('says when it was sent, in words', () => {
    expect(sentWords('2026-11-12T15:04:00Z', { timeZone: 'UTC' })).toBe('Sent Nov 12, 2026 at 3:04 PM');
    expect(sentWords(null)).toBe('');
  });
});
