import { describe, expect, it } from 'vitest';
import { changesState, changesTitle, chatOption, placeholder, runLine, shortDate, windowHint } from './chatWords';

const meta = { ai: { models: [{ key: 'claude-sonnet-5-5', label: 'Sonnet 5.5' }] } };

describe('chat words (D7, D19, D25, D90)', () => {
  it('names a chat by its title, tab and day', () => {
    const now = new Date('2026-11-12T12:00:00Z');
    expect(shortDate('2026-10-14T12:00:00Z', now)).toBe('Oct 14');
    expect(shortDate('2025-10-14T12:00:00Z', now)).toBe('Oct 14, 2025');
    const chat = { number: 2, title: '', tab: 'advisor', last_used_at: null, created_at: '' };
    expect(chatOption(chat)).toBe('Chat 2 · Advisor');
  });

  it('says what a run cost against the deal, with its model (D90)', () => {
    const turn = { status: 'done', cost_usd: '0.0412', model: 'claude-sonnet-5-5' };
    expect(runLine(turn, { usd: '1.2', budget_usd: '25' }, meta)).toBe('This run $0.04 · Deal $1.20 of $25.00 · Sonnet 5.5');
    expect(runLine({ ...turn, status: 'running' }, null, meta)).toBe('');
  });

  it('places the composer and the hint past thirty messages (D19, D25, D104)', () => {
    expect(placeholder({ locked: true })).toMatch(/^Locked/);
    expect(placeholder({ busy: true, locked: true })).toMatch(/answering/);
    expect(windowHint(30)).toBe('');
    expect(windowHint(31)).toMatch(/last 30 messages/);
  });

  it('tells where a turn’s changes stand (D71, D73)', () => {
    const items = [{ id: 't1' }, { id: 't2' }];
    expect(changesState({ items: [] })).toBe('');
    expect(changesTitle({ items, status: 'done', resolution: '' })).toBe('Claude proposes 2 changes');
    expect(changesTitle({ items, resolution: 'applied', landed: { auto: true } })).toBe('✓ Claude changed the table');
    expect(changesState({ items, resolution: 'undone', landed: { undone: true } })).toBe('undone');
  });
});
