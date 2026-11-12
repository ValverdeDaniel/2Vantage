import { describe, expect, it } from 'vitest';
import { FAST_MS, SLOW_MS, finishedJobs, pollInterval, stillWatched } from './aiPolling';

const at = (seconds) => new Date(Date.UTC(2026, 10, 20, 15, 0, seconds)).toISOString();
const now = Date.parse(at(0)) + 1;

describe('pollInterval', () => {
  it('does not poll while nothing is queued or running', () => {
    expect(pollInterval({ jobs: [], recent: [] }, now)).toBe(false);
    expect(pollInterval(undefined, now)).toBe(false);
  });

  it('polls every 2 s at first, slowing to every 10 s while a job keeps running', () => {
    const job = { id: 1, status: 'running', started_at: at(0) };
    const after = (seconds) => pollInterval({ jobs: [job] }, Date.parse(at(0)) + seconds * 1000);
    expect(after(1)).toBe(FAST_MS);
    expect(after(25)).toBe(FAST_MS);
    expect(after(45)).toBe(FAST_MS + 2000);
    expect(after(600)).toBe(SLOW_MS);
  });

  it('times a queued job from when it was queued', () => {
    const queued = { id: 2, status: 'queued', started_at: null, created_at: at(0) };
    expect(pollInterval({ jobs: [queued] }, Date.parse(at(0)) + 300000)).toBe(SLOW_MS);
  });
});

describe('finishedJobs', () => {
  const state = {
    jobs: [{ id: 3, status: 'running' }],
    recent: [
      { id: 1, status: 'done', landed: { areas: ['advisor'] } },
      { id: 2, status: 'cancelled' },
    ],
  };

  it('names the watched jobs that have finished, and only those', () => {
    expect(finishedJobs(new Set([1, 3]), state).map((job) => job.id)).toEqual([1]);
    expect(finishedJobs(new Set(), state)).toEqual([]);
  });

  it('keeps watching active jobs and watched ones not yet seen finished', () => {
    expect([...stillWatched(new Set([1, 9]), state)].sort()).toEqual([3, 9]);
  });
});
