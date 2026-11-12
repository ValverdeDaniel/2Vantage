import { describe, expect, it } from 'vitest';
import {
  endedText,
  failedText,
  landedToast,
  leftOutText,
  readerKinds,
  readsOn,
  runningText,
  summaryLine,
  undoneToast,
} from './readWords';

const meta = { ai: { targets: [{ key: 'quotes', kinds: ['quote', 'renewal'] }] } };
const nameOf = (id) => ({ 9: 'packet.pdf' })[id];

describe('the read door and card words', () => {
  it('knows what each reader reads, and which reads touch these files', () => {
    expect(readerKinds(meta)).toEqual(['quote', 'renewal']);
    expect(readerKinds({})).toEqual([]);
    const jobs = [{ kind: 'read', documents: [9] }, { kind: 'locate', documents: [9] }, { kind: 'read', documents: [4] }];
    expect(readsOn(jobs, [9])).toEqual([jobs[0]]);
  });

  it('says how a read is going and how it ended', () => {
    expect(runningText({ status: 'running', progress: 40, documents: [9], step: 'Reading pages 1–2' })).toEqual({
      text: 'Claude is reading the file · 40%',
      line: 'Reading pages 1–2',
    });
    expect(endedText({ kind: 'read', status: 'failed', error: 'Claude was not called.' })).toBe('Claude was not called.');
    expect(endedText({ kind: 'read', status: 'done', land: 'budget', wait_reason: 'Waits.' })).toBe('Waits.');
    expect(endedText({ kind: 'read', status: 'done', land: 'staged' })).toBe('');
  });

  it('names failed parts and left-out pages with the server’s words', () => {
    expect(failedText([{ doc: 9, where: 'pages 1–2', reason: 'error' }], nameOf, { error: 'no answer' })).toBe(
      'Part of this read could not be finished: packet.pdf, pages 1–2 (no answer). The plans below are what the rest found.',
    );
    expect(leftOutText([{ doc: 9, pages: [3], why: ['header'] }], nameOf, { header: 'only the header' })).toBe(
      'Not read: page 3 of packet.pdf (only the header).',
    );
    expect(failedText([], nameOf, {})).toBe('');
  });

  it('sums a change set up with its model and cost', () => {
    const models = [{ key: 'claude-sonnet-5-5', label: 'Sonnet 5.5' }];
    expect(summaryLine({ summary: '2 current plans', model: 'claude-sonnet-5-5', cost_usd: '0.0412' }, models)).toBe(
      '2 current plans · read with Sonnet 5.5 · $0.04',
    );
  });
});

describe('using and undoing a read (D72, D73)', () => {
  it('says what landed, or that nothing did', () => {
    expect(landedToast({ activity_ids: [4], summary: '2 current plans · 2 renewals' })).toBe(
      'Scan applied — 2 current plans · 2 renewals',
    );
    expect(landedToast({ activity_ids: [], summary: 'Nothing changed.' })).toBe('Nothing changed.');
  });

  it('names the plans an Undo kept', () => {
    expect(undoneToast({ kept: ['Florida Blue PPO'], skipped: [] })).toContain('Florida Blue PPO stayed');
  });
});
