import { useCallback, useState } from 'react';
import { useAiState, useStartLocate, useStopJob } from '../../api/ai';
import { errorText } from '../../lib/errors';
import { useToast } from '../../ui/useToast';
import { STOPPING } from './checkWords';

const sameFiles = (job, ids) => ids.length > 0 && ids.every((id) => job.documents.includes(id));

/*
 * "Check this file" on the station (plan.md §8.16; E59): a `locate` job over the file on screen (or 📚 All proposals'
 * files). The job runs in the worker, so it goes on while the page or the backend restarts; this hook reads it back
 * from `useAiState`: `job` is the check running on these files (started by anyone), `ended` the last one that finished
 * while this page watched. Its areas refetch when it ends (useAiState), so each ↗ opens where the value was found.
 */
export default function useCheckFile(dealId, fileIds) {
  const toast = useToast();
  const [ended, setEnded] = useState(null);
  const key = fileIds.join(',');
  const onFinished = useCallback(
    (job) => {
      if (job.kind === 'locate' && sameFiles(job, key.split(',').map(Number))) setEnded(job);
    },
    [key],
  );
  const state = useAiState(dealId, { onFinished });
  const start = useStartLocate(dealId);
  const stop = useStopJob(dealId);
  const job = (state.data?.jobs || []).find((each) => each.kind === 'locate' && sameFiles(each, fileIds)) || null;

  async function check() {
    setEnded(null);
    try {
      await start.mutateAsync({ documentIds: fileIds });
    } catch (error) {
      toast.error(errorText(error));
    }
  }

  async function halt() {
    if (!job) return;
    try {
      await stop.mutateAsync(job.id);
      toast.info(STOPPING);
    } catch (error) {
      toast.error(errorText(error));
    }
  }

  return {
    job,
    ended: ended && sameFiles(ended, fileIds) ? ended : null,
    busy: Boolean(job) || start.isPending,
    stopping: Boolean(job?.stopping) || stop.isPending,
    check,
    stop: halt,
    dismiss: () => setEnded(null),
  };
}
