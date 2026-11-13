import { describe, expect, it } from 'vitest';
import { activityLook } from './activityLook';

describe('activityLook (M70, M71)', () => {
  it('M71 keeps the violet client tone for whatever the client did', () => {
    expect(activityLook('review', 'client_submitted', true)).toEqual({ tone: 'client', icon: '↙' });
    expect(activityLook('documents', 'created', true).tone).toBe('client');
  });

  it('M71 marks a file received, a signature and a sale as good, with their icons', () => {
    expect(activityLook('documents', 'created')).toEqual({ tone: 'good', icon: '📄' });
    expect(activityLook('questionnaire', 'signed')).toEqual({ tone: 'good', icon: '✒' });
    expect(activityLook('quotes', 'sold')).toEqual({ tone: 'good', icon: '$' });
  });

  it('M71 warns on a loss, a removal and a revert', () => {
    expect(activityLook('deal', 'lost')).toEqual({ tone: 'warn', icon: '✕' });
    expect(activityLook('notes', 'removed').tone).toBe('warn');
    expect(activityLook('intake', 'reverted')).toEqual({ tone: 'warn', icon: '↶' });
  });

  it('M70 reads anything else as information, with the deal opened as a diamond', () => {
    expect(activityLook('deal', 'created')).toEqual({ tone: 'info', icon: '◆' });
    expect(activityLook('notes', 'created')).toEqual({ tone: 'info', icon: '✎' });
    expect(activityLook('saved_views', 'changed')).toEqual({ tone: 'info', icon: '•' });
  });
});
