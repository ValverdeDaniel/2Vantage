import { describe, expect, it } from 'vitest';
import { clientStatuses, creatableStatuses, labelOf, manualStages, relationshipLabel, stageLadder } from './meta';

// The vocabularies come from /api/meta/ (rule 1); these helpers only read them.
const META = {
  stages: [
    { key: 'intake', label: 'Intake' },
    { key: 'quoting', label: 'Quoting' },
    { key: 'proposal', label: 'Proposal' },
    { key: 'sold', label: 'Sold' },
    { key: 'lost', label: 'Lost' },
  ],
  relationships: [
    { key: 'prospect', label: 'Prospect', create: true },
    { key: 'new_client', label: 'New client', create: false },
    { key: 'existing_client', label: 'Existing client', create: true },
  ],
};

describe('stages', () => {
  it('keeps the ladder without lost, and the hand-set stages without sold', () => {
    expect(stageLadder(META).map((s) => s.key)).toEqual(['intake', 'quoting', 'proposal', 'sold']);
    expect(manualStages(META).map((s) => s.key)).toEqual(['intake', 'quoting', 'proposal']);
  });
});

describe('client statuses', () => {
  it('labels each status from the served vocabulary, and a missing one by its key', () => {
    expect(relationshipLabel(META, 'new_client')).toBe('New client');
    expect(relationshipLabel(undefined, 'prospect')).toBe('prospect');
    expect(labelOf(META.stages, 'unknown')).toBe('unknown');
  });

  it('offers only the statuses the server lets a new client start with', () => {
    expect(creatableStatuses(META).map((s) => s.key)).toEqual(['prospect', 'existing_client']);
    expect(creatableStatuses(undefined)).toEqual([]);
  });

  it('CL12 lists every status but Prospect under Clients, in the served order', () => {
    expect(clientStatuses(META).map((s) => s.key)).toEqual(['new_client', 'existing_client']);
    expect(clientStatuses(undefined)).toEqual([]);
  });
});
