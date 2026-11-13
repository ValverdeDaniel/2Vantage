import { describe, expect, it } from 'vitest';
import { DEFAULT_TAB, NAV, navGroups, tabFor, tabLabel } from './nav';

const ALL = NAV.flatMap((group) => group.tabs.map((tab) => tab.key));
const shape = (groups) => groups.map((group) => [group.label, group.tabs.map((tab) => tab.label)]);

describe('the deal sidebar (A21, OQ9)', () => {
  it('A21 keeps old Vantage order and groups exactly', () => {
    expect(shape(navGroups(ALL))).toEqual([
      [null, ['Overview', 'Agenda']],
      ['1 · Get to Market', ['Review & requests', 'Intake', 'Census', 'Questionnaire', 'RFP', 'Commission']],
      ['2 · Quote to Close', ['Advisor', 'Proposal']],
      ['Shared', ['Documents']],
    ]);
  });

  it('A21 uses the path keys of plan.md §8.1', () => {
    expect(ALL).toEqual([
      'overview',
      'agenda',
      'review',
      'intake',
      'census',
      'questionnaire',
      'rfp',
      'commission',
      'advisor',
      'proposal',
      'documents',
    ]);
  });

  it('A21 leaves out tabs not yet built, and a group with none loses its label', () => {
    expect(shape(navGroups(['documents', 'advisor', 'proposal']))).toEqual([
      ['2 · Quote to Close', ['Advisor', 'Proposal']],
      ['Shared', ['Documents']],
    ]);
  });

  it('A21 keeps the old order whatever order the built tabs arrive in', () => {
    expect(shape(navGroups(new Set(['documents', 'census', 'overview'])))).toEqual([
      [null, ['Overview']],
      ['1 · Get to Market', ['Census']],
      ['Shared', ['Documents']],
    ]);
  });
});

describe('the tab in the path (A26, plan.md §8.1)', () => {
  const built = ['overview', 'advisor', 'proposal', 'documents'];

  it('A26 opens a built tab', () => {
    expect(tabFor('documents', built)).toBe('documents');
  });

  it('A26 O.4 sends an unbuilt or unknown tab to the default tab, the Overview from slice 62', () => {
    expect(DEFAULT_TAB).toBe('overview');
    expect(tabFor('census', built)).toBe('overview');
    expect(tabFor('commission', built)).toBe('overview');
    expect(tabFor(undefined, built)).toBe('overview');
  });

  it("A26 reads an old link's tab name: carriers is the RFP tab", () => {
    expect(tabFor('carriers', ['advisor', 'rfp'])).toBe('rfp');
    expect(tabFor('carriers', built)).toBe('overview');
  });

  it('A21 names each tab as the sidebar does', () => {
    expect(tabLabel('rfp')).toBe('RFP');
    expect(tabLabel('review')).toBe('Review & requests');
    expect(tabLabel('nope')).toBe('nope');
  });
});
