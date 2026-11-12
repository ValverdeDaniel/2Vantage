import { describe, expect, it } from 'vitest';
import {
  fileFacts,
  lastRunLine,
  nextModel,
  runningTitle,
  secondsSince,
  sentToast,
  spendLine,
  tabKinds,
} from './drawerWords';

const META = {
  document_kinds: [{ key: 'quote', label: 'Carrier quote' }],
  ai: {
    targets: [
      { key: 'quotes', kinds: ['quote', 'renewal'] },
      { key: 'census', kinds: ['census'] },
    ],
    tabs: { advisor: ['quotes'], census: ['census'], intake: [] },
    models: [
      { key: 'sonnet', label: 'Sonnet 5.5', admins_only: false },
      { key: 'opus', label: 'Opus 5.5', admins_only: true },
    ],
    ladder: ['sonnet', 'opus'],
    default_model: 'sonnet',
  },
};

describe('the drawer words', () => {
  it('D5 reads the kinds a tab reads from meta, and none where each file says what it is', () => {
    expect(tabKinds(META, 'advisor')).toEqual(['quote', 'renewal']);
    expect(tabKinds(META, 'intake')).toEqual([]);
    expect(tabKinds(META, 'documents')).toEqual([]);
    expect(tabKinds({}, 'advisor')).toEqual([]);
  });

  it('D13 names pages, member pages left out and image pages', () => {
    expect(fileFacts({ page_count: 3, screen: { left_out_pages: [2], image_pages: [1, 3] } })).toBe(
      '3 pages · 1 left out (member data) · 2 image pages',
    );
    expect(fileFacts({ page_count: 1, screen: {} })).toBe('1 page');
  });

  it('D8 says the deal against its budget and the last read for everyone', () => {
    expect(spendLine({ usd: '0.1', budget_usd: '25.00' })).toBe('Deal $0.10 of $25.00');
    const recent = [{ kind: 'read', status: 'done', model: 'sonnet', cost_usd: '0.0461' }];
    expect(lastRunLine(recent, META)).toBe('Last read: Sonnet 5.5 · $0.05');
    expect(lastRunLine([], META)).toBe('');
  });

  it('D76 tries again on the next model only for those who may use it', () => {
    expect(nextModel(META, 'sonnet', true)).toBe('opus');
    expect(nextModel(META, 'sonnet', false)).toBe('');
    expect(nextModel(META, 'opus', true)).toBe('');
    expect(nextModel(META, '', true)).toBe('opus');
  });

  it('D22 names the queue place and the files', () => {
    expect(runningTitle({ status: 'queued', queue_position: 1, kind: 'read', documents: [1] })).toBe(
      'Waiting for the job ahead (next)',
    );
    expect(runningTitle({ status: 'running', kind: 'read', documents: [1, 2] })).toBe('Reading 2 files');
  });

  it('D21 counts whole seconds since the job started', () => {
    expect(secondsSince('2026-11-12T10:00:00Z', Date.parse('2026-11-12T10:00:42.9Z'))).toBe(42);
    expect(secondsSince('', 0)).toBe(0);
  });

  it('D16 D17 says what was read and what was only filed', () => {
    expect(sentToast(2, { jobs: [{ status: 'running' }], not_read: [] })).toBe(
      'Attached 2 files — Claude is reading them.',
    );
    expect(sentToast(2, { jobs: [{ status: 'queued', queue_position: 1 }], not_read: [9] })).toBe(
      'Attached 2 files — Claude reads them after the job ahead. 1 of them is only filed.',
    );
    expect(sentToast(1, { jobs: [], not_read: [9] })).toMatch(/^Filed 1 file\./);
  });
});
