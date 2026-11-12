import { describe, expect, it } from 'vitest';
import { issueBlocked, issueWords, latestIssued, nextVersion, summaryWords, ticked } from './packetModel';

const FILES = [{ key: 'pdf' }, { key: 'pptx' }, { key: 'xlsx' }];

describe('the packet card (J96, J103)', () => {
  it('ticks every file unless unticked, in the card order', () => {
    expect(ticked(FILES, {})).toEqual(['pdf', 'pptx', 'xlsx']);
    expect(ticked(FILES, { pptx: false, xlsx: true })).toEqual(['pdf', 'xlsx']);
  });

  it('says how many are ticked and what to check', () => {
    expect(summaryWords(2, 3, null)).toBe('2 of 3 ticked');
    expect(summaryWords(3, 3, [])).toBe('3 of 3 ticked · ✓ Nothing to fix');
    expect(summaryWords(3, 3, [{}, {}])).toBe('3 of 3 ticked · ⚠ 2 to check');
  });

  it('numbers the next version past every earlier one, failed ones too', () => {
    expect(nextVersion([])).toBe(1);
    expect(nextVersion([{ version: 2, state: 'failed' }, { version: 1, state: 'issued' }])).toBe(3);
    expect(latestIssued([{ version: 2, state: 'failed' }, { version: 1, state: 'issued' }]).version).toBe(1);
  });

  it('words a building, a failed and a waiting version', () => {
    const building = { version: 2, state: 'building', job: { status: 'running', progress: 30, step: 'Drawing the PDF' } };
    expect(issueWords(building)).toBe('Building the files · 30% — Drawing the PDF');
    expect(issueWords({ ...building, job: { status: 'queued' } })).toBe('Waiting to start building the files');
    expect(issueWords({ version: 1, state: 'failed', error: 'Retry.' })).toBe('Could not be built: Retry.');
    expect(issueBlocked({ building, saving: false })).toBe('Proposal v2 is still being built.');
    expect(issueBlocked({ building: null, saving: true })).toBe('Saving your changes first…');
    expect(issueBlocked({ building: null, saving: false })).toBe('');
  });
});
