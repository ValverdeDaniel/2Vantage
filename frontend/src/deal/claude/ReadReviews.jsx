import { useState } from 'react';
import { useAiState, useStopJob } from '../../api/ai';
import { useMeta } from '../../api/meta';
import CensusReadCard from './CensusReadCard';
import LandedStrip from './LandedStrip';
import { endedText, readerKinds, readsOn, runningText } from './readWords';
import { RENDERERS } from './renderers';
import RecheckCard from './RecheckCard';
import ReviewCard from './ReviewCard';

/*
 * Claude's reads of the files on screen (plan.md §8.16, §10.4, §10.5; D23, D28, D29, D73, E78; slices 18–19), mounted
 * under the Documents station: the old Claude strip while a read runs (progress and Stop), why a read ended without a
 * change set (failed, or waiting past its cost cap), the staged review card for each change set waiting on these
 * files, and, for a read used in the last minutes, what it wrote with ↶ Undo this run. Shown only when Claude is set up
 * (D26). Reads start from the station's ↻ Re-read… panel (E75) and, from slice 20, the drawer. `onOpen(doc, page)`
 * shows a staged value's page in the station's viewer (E78's pin).
 */
export default function ReadReviews({ dealId, files, onOpen }) {
  const { data: meta } = useMeta();
  const [dismissed, setDismissed] = useState(new Set());
  const ai = useAiState(dealId);
  const stop = useStopJob(dealId);
  const state = ai.data;
  if (!state?.claude || !meta?.ai) return null;
  // the SBC reader's files too (slice 22), and the census and intake readers' (slice 51)
  const kinds = ['quotes', 'sbc', 'census', 'intake'].flatMap((target) => readerKinds(meta, target));
  const ids = files.filter((file) => kinds.includes(file.kind) && !file.archived_at).map((file) => file.id);
  if (!ids.length) return null;
  const nameOf = (id) => files.find((file) => file.id === id)?.display_name || '';
  const onThese = (row) => row.documents.some((id) => ids.includes(id));
  const waiting = (state.waiting || []).filter(onThese);
  const landed = (state.news || []).filter((row) => row.type === 'landed' && onThese(row) && !dismissed.has(row.job_id));
  const [running] = readsOn(state.jobs, ids);
  const ended = readsOn(state.recent, ids).find((job) => endedText(job) && !dismissed.has(job.id));
  const dismiss = (id) => setDismissed(new Set([...dismissed, id]));

  return (
    <div className="bb-mt" data-read-reviews>
      {running && (
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
      )}
      {!running && ended && (
        <div className="bnf-claude-strip bnf-claude-strip-news bnf-claude-strip-failed" role="status">
          <span className="bnf-claude-strip-text">{endedText(ended)}</span>
          <button type="button" className="bnf-claude-strip-x" aria-label="Dismiss" onClick={() => dismiss(ended.id)}>
            ✕
          </button>
        </div>
      )}
      {landed.map((row) => (
        <LandedStrip key={row.job_id} dealId={dealId} news={row} onDismiss={() => dismiss(row.job_id)} />
      ))}
      {waiting.map((row) =>
        row.kind === 'recheck' ? (
          <RecheckCard key={row.job_id} dealId={dealId} jobId={row.job_id} nameOf={nameOf} onOpen={onOpen} />
        ) : row.target === 'census' ? (
          <CensusReadCard key={row.job_id} dealId={dealId} jobId={row.job_id} nameOf={nameOf} />
        ) : (
          <ReviewCard
            key={row.job_id}
            dealId={dealId}
            jobId={row.job_id}
            renderer={RENDERERS[row.target]}
            meta={meta}
            nameOf={nameOf}
            onOpen={onOpen}
          />
        ),
      )}
    </div>
  );
}
