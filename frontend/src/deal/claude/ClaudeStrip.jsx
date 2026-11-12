import { useStopJob } from '../../api/ai';
import { errorText } from '../../lib/errors';
import { useToast } from '../../ui/useToast';
import { claudeDoor } from './door';
import { stripDoing } from './drawerWords';
import LandedStrip from './LandedStrip';
import RecheckOffer from './RecheckOffer';

/*
 * The Claude strip over the tables Claude reads into (plan.md §8.4, §8.17; A25, D34, D71; the old CaseWorkspace's
 * ClaudeStrip), from the one poll (`useAiState`), one line at a time:
 * - what Claude is doing, with Stop (every kind can stop, B20);
 * - a read waiting for review: nothing on the table has changed — Review ▸ opens the drawer on it;
 * - a read used in the last minutes, by a person or by itself: what it wrote, ↶ Undo this run and ↻ Try again;
 * - a read that failed, or waits past its cost cap (Review ▸ opens the drawer's over-budget card).
 * - past the server's count of flags, "✦ Re-check N flags ▸" (E80; slice 22, `RecheckOffer`).
 * - ⚖ Rank's stars (slice 37, D36) as their own news with ↶ Undo this run, and a rank that failed, in its words.
 */
export default function ClaudeStrip({ dealId, state, dismissed, retryFor }) {
  const toast = useToast();
  const stop = useStopJob(dealId);
  const [running] = state.jobs || [];
  const close = (id) => (
    <button type="button" className="bnf-claude-strip-x" aria-label="Dismiss" onClick={() => claudeDoor.dismiss(id)}>
      ✕
    </button>
  );

  if (running) {
    const press = async () => {
      try {
        await stop.mutateAsync(running.id);
        toast.info('Stopping — what Claude finished is kept for review.');
      } catch (error) {
        toast.error(errorText(error));
      }
    };
    return (
      <div className="bnf-claude-strip" role="status" data-claude-strip="running">
        <span className="bb-dot-pulse" aria-hidden="true" />
        <span className="bnf-claude-strip-text">
          {stripDoing(running)}
          {running.step ? <span className="bnf-claude-strip-line"> — {running.step}</span> : null}
        </span>
        <button type="button" className="btn btn-secondary btn-sm" disabled={running.stopping} onClick={press}>
          {running.stopping ? 'Stopping…' : 'Stop'}
        </button>
      </div>
    );
  }
  const waiting = (state.waiting || []).filter((row) => !dismissed.includes(row.job_id));
  if (waiting.length) {
    return (
      <div className="bnf-claude-strip bnf-claude-strip-news" data-claude-strip="waiting">
        <span className="bnf-claude-strip-text">
          ✦ Claude’s read waits for your review — nothing on the table has changed.
        </span>
        <button type="button" className="btn btn-primary btn-sm" onClick={() => claudeDoor.open()}>
          Review ▸
        </button>
        {close(waiting[0].job_id)}
      </div>
    );
  }
  const landed = (state.news || []).find((row) => row.type === 'landed' && !dismissed.includes(row.job_id));
  if (landed) {
    return (
      <LandedStrip
        dealId={dealId}
        news={landed}
        retry={landed.kind === 'rank' ? null : retryFor(landed)}
        onDismiss={() => claudeDoor.dismiss(landed.job_id)}
      />
    );
  }
  const ended = (state.recent || []).find(
    (job) =>
      ((job.kind === 'read' && (job.status === 'failed' || job.land === 'budget')) ||
        (job.kind === 'rank' && job.status === 'failed')) && // a rank that could not star (slice 37)
      !dismissed.includes(job.id),
  );
  if (!ended) return <RecheckOffer dealId={dealId} flags={state.flags} dismissed={dismissed} />;
  return (
    <div className="bnf-claude-strip bnf-claude-strip-news bnf-claude-strip-failed" data-claude-strip="ended">
      <span className="bnf-claude-strip-text">
        {ended.status !== 'failed'
          ? ended.wait_reason
          : ended.kind === 'rank'
            ? `⚖ Rank: ${ended.error || 'the ranking failed'}`
            : `Claude stopped: ${ended.error || 'the read failed'}`}
      </span>
      {ended.land === 'budget' && (
        <button type="button" className="btn btn-secondary btn-sm" onClick={() => claudeDoor.open()}>
          Review ▸
        </button>
      )}
      {close(ended.id)}
    </div>
  );
}
