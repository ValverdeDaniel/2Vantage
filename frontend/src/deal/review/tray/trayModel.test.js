import { describe, expect, it } from 'vitest';
import { byDestination, bySection, destinationOf, possessive, sentWords } from './trayModel';

const NOW = new Date('2026-11-12T15:00:00Z');
const dana = { key: 'request:1', names: ['Dana Diaz'], expires_at: '2026-11-18T15:00:00Z' };
const joe = { key: 'request:2', names: ['Joe Example'], expires_at: '2026-11-20T15:00:00Z' };
const SECTIONS = [
  { key: 'census', label: 'Census' },
  { key: 'intake', label: 'Intake' },
  { key: 'documents', label: 'Documents' },
];

describe('L49 the tray bar says where its items go', () => {
  it('names one link with its expiry, and a lapsed one as living again', () => {
    expect(destinationOf([{ target: dana, why: '' }], NOW)).toBe('→ Dana’s link (expires Nov 18)');
    const lapsed = { ...dana, expires_at: '2026-11-01T00:00:00Z' };
    expect(destinationOf([{ target: lapsed, why: '' }], NOW)).toBe('→ Dana’s link (lives again when sent)');
  });
  it('names several links, and what needs a new one', () => {
    const items = [{ target: dana, why: '' }, { target: joe, why: '' }, { target: null, why: 'No open link' }];
    expect(destinationOf(items, NOW)).toBe('→ Dana’s and Joe’s links · 1 needs a new link');
    expect(destinationOf([{ target: null, why: 'x' }], NOW)).toBe('→ needs a new link');
    expect(destinationOf([{ target: null, why: 'x', gone: true }], NOW)).toBe('');
  });
  it('says "their" for a link that names nobody', () => {
    expect(possessive([])).toBe('their');
    expect(possessive(['a@example.test'])).toBe('a@example.test’s');
  });
});

describe('L50 L53 the tray groups its items', () => {
  const items = [
    { id: 1, surface: 'intake', target: dana, why: '' },
    { id: 2, surface: 'census', target: null, why: 'Needs a PIN' },
    { id: 3, surface: 'documents', target: dana, why: '' },
    { id: 4, surface: 'intake', target: joe, why: '' },
    { id: 5, surface: 'intake', gone: true },
  ];
  it('by section, in the sections’ order, empty ones left out', () => {
    expect(bySection(items, SECTIONS).map((group) => [group.key, group.list.map((item) => item.id)])).toEqual([
      ['census', [2]],
      ['intake', [1, 4, 5]],
      ['documents', [3]],
    ]);
  });
  it('by destination, then what needs a new link, then what is gone', () => {
    const found = byDestination(items);
    expect(found.links.map((group) => [group.key, group.list.map((item) => item.id)])).toEqual([
      ['request:1', [1, 3]],
      ['request:2', [4]],
    ]);
    expect(found.nowhere.map((item) => item.id)).toEqual([2]);
    expect(found.gone.map((item) => item.id)).toEqual([5]);
  });
  it('words a send', () => {
    expect(sentWords({ sent: 3, targets: [{ names: ['Dana Diaz'] }] })).toBe('Sent 3 items on Dana’s link');
    expect(sentWords({ sent: 4, targets: [{ names: [] }, { names: [] }] })).toBe('Sent 4 items on 2 links');
    expect(sentWords({ sent: 0, targets: [] })).toBe('Nothing went: no open link could take it');
  });
});
