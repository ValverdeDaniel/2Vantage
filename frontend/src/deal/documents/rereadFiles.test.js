import { describe, expect, it } from 'vitest';
import { firstPicks, readKinds, rereadable } from './rereadFiles';

const meta = { ai: { targets: [{ key: 'quotes', kinds: ['quote', 'renewal'] }] } };
const files = [
  { id: 1, kind: 'quote' },
  { id: 2, kind: 'census' },
  { id: 3, kind: 'renewal' },
  { id: 4, kind: 'quote', archived_at: '2026-11-01' },
];

describe('E75 the Re-read panel', () => {
  it('offers every kind the quote reader reads, never a removed file, and nothing without Claude', () => {
    expect(rereadable(files, meta).map((file) => file.id)).toEqual([1, 3]);
    expect(readKinds({})).toEqual([]);
  });

  it('opens with the file on screen ticked, or every offered file under All proposals', () => {
    const offered = rereadable(files, meta);
    expect([...firstPicks(offered, files[2], false)]).toEqual([3]);
    expect([...firstPicks(offered, files[1], false)]).toEqual([]);
    expect([...firstPicks(offered, null, true)]).toEqual([1, 3]);
  });
});
