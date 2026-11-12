import { useState } from 'react';
import { useAiState, useStartRead, useStopJob } from '../../api/ai';
import { useMeta } from '../../api/meta';
import { errorText } from '../../lib/errors';
import { useToast } from '../../ui/useToast';
import { QuoteReview } from '../advisor';
import { endedText, readerKinds, readsOn, runningText } from './readWords';
import ReviewCard from './ReviewCard';

/*
 * Claude's reads of the files on screen (plan.md §8.16, §10.4, §10.5; D28, D29, D39; slice 18), mounted under the
 * Documents station: the read door for the files a reader reads ("✦ Read with Claude", the one read door,
 * `deals/{id}/ai/reads/`), the old Claude strip while a read runs (progress and Stop), why a read ended without a
 * change set (failed, or waiting past its cost cap), and the staged review card for each change set waiting on these
 * files. Shown only when Claude is set up (D26). The Re-read panel (E75) and the drawer (D14) are slices 19 and 20's
 * doors to the same endpoint.
 */
const RENDERERS = { quotes: QuoteReview };

export default function ReadReviews({ dealId, files }) {
  const toast = useToast();
  const { data: meta } = useMeta();
  const [dismissed, setDismissed] = useState(new Set());
  const ai = useAiState(dealId);
  const start = useStartRead(dealId);
  const stop = useStopJob(dealId);
  const state = ai.data;
  if (!state?.claude || !meta?.ai) return null;
  const kinds = readerKinds(meta);
  const ids = files.filter((file) => kinds.includes(file.kind) && !file.archived_at).map((file) => file.id);
  if (!ids.length) return null;
  const nameOf = (id) => files.find((file) => file.id === id)?.display_name || '';
  const waiting = (state.waiting || []).filter((row) => row.documents.some((id) => ids.includes(id)));
  const [running] = readsOn(state.jobs, ids);
  const ended = readsOn(state.recent, ids).find((job) => endedText(job) && !dismissed.has(job.id));

  async function read() {
    try {
      await start.mutateAsync({ documentIds: ids });
    } catch (error) {
      toast.error(errorText(error));
    }
  }

  return (
    <div className="bb-mt" data-read-reviews>
      {running ? (
        <div className="bnf-claude-strip" role="status" data-read-job={running.id} data-read-status={running.status}>
          <span className="bb-dot-pulse" aria-hidden="true" />
          <span className="bnf-claude-strip-text">
            {runningText(running).text}
            {running.step ? <span className="bnf-claude-strip-line"> — {running.step}</span> : null}
          </span>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            disabled={running.stopping || stop.isPending}
            onClick={() => stop.mutate(running.id)}
          >
            {running.stopping ? 'Stopping…' : 'Stop'}
          </button>
        </div>
      ) : (
        !waiting.length && (
          <div className="bnf-doc-controls">
            <button type="button" className="btn btn-secondary btn-sm" disabled={start.isPending} onClick={read}>
              ✦ Read with Claude
            </button>
            <span className="bb-subtitle">
              Claude reads {ids.length > 1 ? 'these files' : 'this file'} into plans you review here before anything
              changes.
            </span>
          </div>
        )
      )}
      {!running && ended && (
        <div className="bnf-claude-strip bnf-claude-strip-news bnf-claude-strip-failed" role="status">
          <span className="bnf-claude-strip-text">{endedText(ended)}</span>
          <button
            type="button"
            className="bnf-claude-strip-x"
            aria-label="Dismiss"
            onClick={() => setDismissed(new Set([...dismissed, ended.id]))}
          >
            ✕
          </button>
        </div>
      )}
      {waiting.map((row) => (
        <ReviewCard
          key={row.job_id}
          dealId={dealId}
          jobId={row.job_id}
          renderer={RENDERERS[row.target]}
          meta={meta}
          nameOf={nameOf}
        />
      ))}
    </div>
  );
}
