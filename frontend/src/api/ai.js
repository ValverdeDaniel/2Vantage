// The ai app (plan.md §7.5, §10.2; O.4, D.6). Query key ['deal', id, 'ai'] for the deal's AI state.
//
// `useAiState` is the browser's one AI poller: it polls `GET deals/{id}/ai/` only while a job is queued or running
// (aiPolling.js), and when a job it watched finishes it refetches the areas the job landed in
// (['deal', id, area]) and every open value source (['value-source']), then tells `onFinished`. Starting or stopping
// a job refetches the state at once.
import { useEffect, useRef } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import api from './client';
import { dealKey } from './deals';
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
