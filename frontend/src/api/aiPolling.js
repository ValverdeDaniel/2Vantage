/*
 * How `useAiState` polls and what it learns (plan.md §3.9, §10.2; O.4, D.6). Pure, so Vitest pins it.
 *
 * The browser polls only while a job is queued or running on the deal: every 2 s at first, then a second slower for
 * every 10 s the oldest job has run, up to every 10 s. Idle, it does not poll: a job started here refetches the state
 * at once, and a tab opened later reads it on open (staleTime 0).
 */

export const FAST_MS = 2000;
export const SLOW_MS = 10000;
const QUICK_SECONDS = 20; // a job this young is polled at the fast rate

const ACTIVE = new Set(['queued', 'running']);

export function isActive(job) {
  return Boolean(job) && ACTIVE.has(job.status);
}

/** Milliseconds until the next poll, or false when nothing is queued or running. */
export function pollInterval(state, now = Date.now()) {
  const jobs = state?.jobs || [];
  if (!jobs.length) return false;
  const started = jobs.map((job) => Date.parse(job.started_at || job.created_at)).filter((t) => !Number.isNaN(t));
  if (!started.length) return FAST_MS;
  const seconds = Math.max(0, (now - Math.min(...started)) / 1000);
  const slower = Math.max(0, Math.floor((seconds - QUICK_SECONDS) / 10)) * 1000;
  return Math.min(SLOW_MS, FAST_MS + slower);
}

/**
 * The jobs that were active (`watched`: ids seen queued or running, or just started here) and have finished in this
 * state: each one is in `recent` now. Their landed areas are refetched and their news shown once.
 */
export function finishedJobs(watched, state) {
  if (!state || !watched?.size) return [];
  const active = new Set((state.jobs || []).map((job) => job.id));
  return (state.recent || []).filter((job) => watched.has(job.id) && !active.has(job.id));
}

/** The ids to keep watching after this state: every active job, and watched ones not yet seen finished. */
export function stillWatched(watched, state) {
  const next = new Set((state?.jobs || []).map((job) => job.id));
  const finished = new Set((state?.recent || []).map((job) => job.id));
  (watched || new Set()).forEach((id) => {
    if (!finished.has(id)) next.add(id);
  });
  return next;
}
