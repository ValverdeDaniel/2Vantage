import { describe, expect, it } from 'vitest';
import { badgeFor } from './badges';

const row = (value, source, status = '') => ({ value, source, status });

describe('the badge per answer (B6)', () => {
  it('says Missing for a needed blank, a dash for an optional one', () => {
    expect(badgeFor(row('', null, 'missing'))).toMatchObject({ label: 'Missing', className: 'bb-badge-rose' });
    expect(badgeFor(row([], null)).label).toBe('—');
  });

  it('says Verified only where a person stands behind the answer', () => {
    for (const origin of ['typed', 'relay', 'client']) {
      expect(badgeFor(row('x', { origin })).label).toBe('Verified ✓');
    }
    expect(badgeFor(row('x', { origin: 'ai', confirmed: { by: 1 } })).label).toBe('Verified ✓');
    expect(badgeFor(row('x', { origin: 'ai' })).label).toBe('Read by AI');
    expect(badgeFor(row('x', { origin: 'import' })).label).toBe('On file');
    expect(badgeFor(row('x', null)).label).toBe('On file');
  });

  it('puts a review mark or an open warning first', () => {
    const flagged = row('x', { origin: 'typed', mark: { state: 'check' } }, 'to_check');
    expect(badgeFor(flagged).label).toBe('⚑ Needs checking');
    const doubted = badgeFor(row('x', { origin: 'ai', low: 'two figures', page: 2 }, 'to_check'));
    expect(doubted).toMatchObject({ label: 'Review', className: 'bb-badge-amber' });
    expect(doubted.title).toContain('page 2');
    expect(doubted.title).toContain('two figures');
    expect(badgeFor(row('x', { origin: 'ai', low: 'blurred', mark: { state: 'ignored' } })).label).toBe('Ignored');
  });
});
