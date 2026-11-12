import { describe, expect, it } from 'vitest';
import { checkLabel, finishedWords, locWords, runningWords } from './checkWords';

describe('Check this file words', () => {
  it('labels the button by how many files it checks', () => {
    expect(checkLabel(1, false)).toBe('Check this file');
    expect(checkLabel(3, false)).toBe('Check these files');
    expect(checkLabel(1, true)).toBe('Checking…');
  });

  it('says what a running or waiting check is doing', () => {
    const running = { status: 'running', progress: 40, step: 'Reading page 120 of 1,500' };
    expect(runningWords(running, 1)).toEqual({
      text: 'Checking the values against this file · 40%',
      line: 'Reading page 120 of 1,500',
    });
    expect(runningWords({ status: 'queued', queue_position: 2 }, 1).line).toBe('another check on this deal runs first');
  });

  it('says how a check ended, in the old toast’s words', () => {
    const counts = (checked, absent) => ({ status: 'done', counts: { checked, absent } });
    expect(finishedWords(counts(12, 2), 1).text).toBe('Checked 12 values against the file — 2 not found in it');
    expect(finishedWords(counts(1, 0), 1).text).toBe('Checked 1 value against the file');
    expect(finishedWords(counts(0, 0), 1).text).toBe('Every value here is already checked');
    expect(finishedWords({ status: 'cancelled' }, 1).tone).toBe('news');
    expect(finishedWords({ status: 'failed', error: 'Try again.' }, 1)).toEqual({
      tone: 'failed',
      text: 'The check stopped: Try again.',
    });
  });

  it('names what the locator found for a value opened from its cell', () => {
    expect(locWords({ state: 'absent' }).text).toBe('Not in the file');
    expect(locWords({ state: 'weak', page: 2 }).text).toBe('Check by eye');
    expect(locWords({ state: 'nocheck', why: 'no_text' }).text).toBe('Check by eye');
    expect(locWords({ state: 'nocheck', why: 'choice' })).toBeNull();
    expect(locWords({ state: 'found', page: 2 })).toBeNull();
    expect(locWords(null)).toBeNull();
  });
});
