// The ai app (plan.md §7.5, §10.2; O.4, D.6). Query key ['deal', id, 'ai'] for the deal's AI state.
//
// `useAiState` is the browser's one AI poller: it polls `GET deals/{id}/ai/` only while a job is queued or running
// (aiPolling.js), and when a job it watched finishes it refetches the areas the job landed in
// (['deal', id, area]) and every open value source (['value-source']), then tells `onFinished`. Starting or stopping
// a job refetches the state at once.
import { useEffect, useRef } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import api from './client';
import { dealKey, invalidateDeal } from './deals';
import { finishedJobs, pollInterval, stillWatched } from './aiPolling';

export const aiKey = (dealId) => dealKey(dealId, 'ai');

// Jobs started in this page, per deal: every useAiState watches them, so a job that finished before the next poll
// still lands (a quick check, or one that ran while the backend restarted).
const started = new Map();

function startedOn(dealId) {
  const id = Number(dealId);
  if (!started.has(id)) started.set(id, new Set());
  return started.get(id);
}

export function watchJob(dealId, job) {
  if (job?.id) startedOn(dealId).add(job.id);
}

export function useAiState(dealId, { onFinished } = {}) {
  const queryClient = useQueryClient();
  const watchedRef = useRef(new Set()); // ids this hook saw active and has not yet seen finish
  const reportedRef = useRef(new Set()); // ids whose end this hook has reported
  const finishedRef = useRef(onFinished);
  useEffect(() => {
    finishedRef.current = onFinished;
  }, [onFinished]);
  const query = useQuery({
    queryKey: aiKey(dealId),
    queryFn: async () => (await api.get(`deals/${dealId}/ai/`)).data,
    staleTime: 0,
    refetchInterval: (current) => pollInterval(current.state.data),
  });
  const { data } = query;
  useEffect(() => {
    if (!data) return;
    const watched = new Set([...watchedRef.current, ...startedOn(dealId)]);
    reportedRef.current.forEach((id) => watched.delete(id));
    const done = finishedJobs(watched, data);
    watchedRef.current = stillWatched(watched, data);
    done.forEach((job) => {
      reportedRef.current.add(job.id);
      (job.landed?.areas || []).forEach((area) => queryClient.invalidateQueries({ queryKey: dealKey(dealId, area) }));
      queryClient.invalidateQueries({ queryKey: ['value-source'] });
    });
    if (done.length) done.forEach((job) => finishedRef.current?.(job));
  }, [data, dealId, queryClient]);
  return query;
}

function useJobWrite(dealId, mutationFn) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSuccess: (job) => {
      watchJob(dealId, job);
      queryClient.invalidateQueries({ queryKey: aiKey(dealId) });
    },
  });
}

/** "Check this file" (E59): ({documentIds, recheck}) → the job (201 new, or 200 the same check already going). */
export function useStartLocate(dealId) {
  return useJobWrite(
    dealId,
    async ({ documentIds, recheck = false }) =>
      (await api.post(`deals/${dealId}/ai/locate/`, { document_ids: documentIds, recheck })).data,
  );
}

/** Stop (D22): (jobId) → the job. A queued job ends at once; a running one at its next step, keeping what it did. */
export function useStopJob(dealId) {
  return useJobWrite(dealId, async (jobId) => (await api.post(`ai/jobs/${jobId}/cancel/`)).data);
}

/**
 * The one read door (D39): ({documentIds, target, pages, model, budgetOverride, review}) → the read job (201 new, or
 * 200 the same read already going). Without a key the server answers 409 with a sentence (D26). `review` makes the read
 * wait for review whoever starts it (the Re-read panel, E75).
 */
export function useStartRead(dealId) {
  return useJobWrite(
    dealId,
    async ({ documentIds, target = 'quotes', pages, model, budgetOverride, review }) =>
      (
        await api.post(`deals/${dealId}/ai/reads/`, {
          document_ids: documentIds,
          target,
          ...(pages ? { pages } : {}),
          ...(model ? { model } : {}),
          ...(budgetOverride ? { budget_override: true } : {}),
          ...(review ? { review: true } : {}),
        })
      ).data,
  );
}

export const jobKey = (jobId) => ['ai-job', Number(jobId)];

/** One job with its change set (D28): fetched when a card shows it; it changes only by Discard, apply or Undo. */
export function useJob(jobId, { enabled = true } = {}) {
  return useQuery({
    queryKey: jobKey(jobId),
    queryFn: async () => (await api.get(`ai/jobs/${jobId}/`)).data,
    enabled: Boolean(jobId) && enabled,
    staleTime: 0,
  });
}

/** Discard (D74): (jobId) → the job, its change set dropped. Nothing on the deal changes. */
export function useDiscardRead(dealId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (jobId) => (await api.post(`ai/jobs/${jobId}/discard/`)).data,
    onSuccess: (job) => {
      queryClient.setQueryData(jobKey(job.id), job);
      queryClient.invalidateQueries({ queryKey: aiKey(dealId) });
    },
  });
}

/** After a read is used or undone: the job as answered, and every query of the deal (plans, counts, stage, history). */
function useLanding(dealId, mutationFn) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSuccess: ({ job }) => {
      queryClient.setQueryData(jobKey(job.id), job);
      invalidateDeal(queryClient, dealId, { header: true });
      queryClient.invalidateQueries({ queryKey: ['value-source'] });
    },
  });
}

/**
 * "Use this scan ▸" / "Apply N selected ▸" (D72): ({jobId, select, picks}) → {job, landed}. No `select` uses the read
 * as proposed; `select` names the items (and "<item>:<key>" values) to use; `picks` places "Which current plan?" items.
 */
export function useApplyRead(dealId) {
  return useLanding(
    dealId,
    async ({ jobId, select, picks }) =>
      (
        await api.post(`ai/jobs/${jobId}/apply/`, {
          ...(select ? { select } : {}),
          ...(picks && Object.keys(picks).length ? { picks } : {}),
        })
      ).data,
  );
}

/** ↶ Undo this run (D73): ({jobId, force}) → {job, undone}. A 409 with `can_force` offers "Undo anyway". */
export function useUndoRead(dealId) {
  return useLanding(
    dealId,
    async ({ jobId, force = false }) => (await api.post(`ai/jobs/${jobId}/undo/`, force ? { force: true } : {})).data,
  );
}

/**
 * Attaching is the request (D16, D17): ({dealId, documentIds, model, budgetOverride}) → {jobs, not_read}. The files
 * just attached are read by the reader of their kind, one read per reader, in the send order; a drop is never refused
 * (the reads queue). Takes the deal id when called: the quote-first door attaches to a deal it made a moment ago.
 */
export function useSendFiles() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ dealId, documentIds, model, budgetOverride }) =>
      (
        await api.post(`deals/${dealId}/ai/sends/`, {
          document_ids: documentIds,
          ...(model ? { model } : {}),
          ...(budgetOverride ? { budget_override: true } : {}),
        })
      ).data,
    onSuccess: (sent, { dealId }) => {
      sent.jobs.forEach((job) => watchJob(dealId, job));
      queryClient.invalidateQueries({ queryKey: aiKey(dealId) });
    },
  });
}

/**
 * ↻ Try again (D76) and Run anyway (D24): ({jobId, model, force, budgetOverride}) → the new read. A read that was used
 * is undone first (a 409 with `can_force` offers "Undo anyway", sent as `force`); one waiting is discarded.
 */
export function useRetryRead(dealId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ jobId, model, force, budgetOverride }) =>
      (
        await api.post(`ai/jobs/${jobId}/retry/`, {
          ...(model ? { model } : {}),
          ...(force ? { force: true } : {}),
          ...(budgetOverride ? { budget_override: true } : {}),
        })
      ).data,
    onSuccess: (job, { jobId }) => {
      watchJob(dealId, job);
      queryClient.invalidateQueries({ queryKey: jobKey(jobId) });
      invalidateDeal(queryClient, dealId, { header: true });
    },
  });
}
