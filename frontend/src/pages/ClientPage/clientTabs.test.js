import { describe, expect, it } from 'vitest';
import { backLink, CLIENT_NAV, clientNavGroups, clientPath, clientTabFor, navBadges, rollupChip } from './clientTabs';

describe('the client page nav (CL13)', () => {
  it('keeps the old order and groups: Overview · Upkeep · Revenue · Relationship', () => {
    expect(CLIENT_NAV.map((group) => group.label)).toEqual([null, 'Upkeep', 'Revenue', 'Relationship']);
    expect(CLIENT_NAV.flatMap((group) => group.tabs.map((tab) => tab.key))).toEqual([
      'overview',
      'agenda',
      'commissions',
      'notes',
    ]);
  });

  it('leaves out tabs not yet built, with their group label', () => {
    const groups = clientNavGroups(['overview', 'notes']);
    expect(groups.map((group) => group.label)).toEqual([null, 'Relationship']);
    expect(clientNavGroups().map((group) => group.label)).toEqual([null, 'Upkeep', 'Revenue', 'Relationship']);
  });

  it('opens the Overview for an unknown or unbuilt tab', () => {
    expect(clientTabFor('notes')).toBe('notes');
    expect(clientTabFor('agenda', ['overview', 'notes'])).toBe('overview');
    expect(clientTabFor('commissions')).toBe('commissions');
    expect(clientTabFor('plan-years')).toBe('overview');
    expect(clientTabFor(undefined)).toBe('overview');
    expect(clientPath(12)).toBe('/clients/12/overview');
  });

  it('goes back to Prospects for a prospect, else to Clients', () => {
    expect(backLink('prospect')).toEqual({ to: '/', label: '← Prospects' });
    expect(backLink('new_client')).toEqual({ to: '/?view=book', label: '← Clients' });
  });
});

describe('the badges and the rollup chip (CL13, CL24, CL25)', () => {
  it('Agenda wears the overdue count; Commissions an amber 1 while no primary producer is set', () => {
    const counts = { overdue: 2, soon: 1, total: 5 };
    expect(navBadges({ owner: null }, counts)).toEqual({
      agenda: { count: 2, tone: 'rose' },
      commissions: { count: 1, tone: 'amber' },
    });
    expect(navBadges({ owner: { id: 3, name: 'Dev' } }, { overdue: 0 }).commissions.count).toBe(0);
  });

  it('says overdue first, then due soon, else on track', () => {
    expect(rollupChip({ overdue: 2, soon: 1 })).toEqual({ label: '2 overdue', className: 'bb-badge bb-badge-rose' });
    expect(rollupChip({ overdue: 0, soon: 3 })).toEqual({ label: '3 due soon', className: 'bb-badge bb-badge-amber' });
    expect(rollupChip({ overdue: 0, soon: 0, total: 4 }).label).toBe('on track');
  });
});
