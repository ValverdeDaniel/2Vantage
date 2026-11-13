import { describe, expect, it } from 'vitest';
import { backLink, CLIENT_NAV, clientNavGroups, clientPath, clientTabFor } from './clientTabs';

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
    expect(clientNavGroups(['overview', 'agenda', 'commissions', 'notes']).length).toBe(4);
  });

  it('opens the Overview for an unknown or unbuilt tab', () => {
    expect(clientTabFor('notes')).toBe('notes');
    expect(clientTabFor('agenda', ['overview', 'notes'])).toBe('overview');
    expect(clientTabFor(undefined)).toBe('overview');
    expect(clientPath(12)).toBe('/clients/12/overview');
  });

  it('goes back to Prospects for a prospect, else to Clients', () => {
    expect(backLink('prospect')).toEqual({ to: '/', label: '← Prospects' });
    expect(backLink('new_client')).toEqual({ to: '/?view=book', label: '← Clients' });
  });
});
