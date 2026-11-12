import { useNavigate } from 'react-router';
import { useRetryRead } from '../../api/ai';
import { errorText } from '../../lib/errors';
import { useToast } from '../../ui/useToast';
import { claudeDoor } from './door';
import LandedStrip from './LandedStrip';
import OverBudget from './OverBudget';
import { RENDERERS } from './renderers';
import ReviewCard from './ReviewCard';
import RunningCard from './RunningCard';

/*
 * What Claude is doing and did on the deal, in the drawer (plan.md §8.17, §10.5; D21–D24, D28, D31, D71, D73, D76):
 * the running cards with Stop; a read that waits past a cap (Run anyway or Dismiss); a read that failed, with ↻ Try
 * again; reads used in the last minutes, by a person or by themselves, with ↶ Undo this run; and every change set
 * waiting for review as its "Review this scan" card — on Documents only a line, since the card shows there under its
 * file. A value's ↗ opens its page on Documents.
 */
function Failed({ dealId, job, onDismiss }) {
  const toast = useToast();
  const retry = useRetryRead(dealId);
  async function again() {
    try {
      await retry.mutateAsync({ jobId: job.id, model: job.model });
      onDismiss();
    } catch (error) {
      toast.error(errorText(error));
    }
  }
  return (
    <div className="bnf-claude-strip bnf-claude-strip-news bnf-claude-strip-failed" role="status">
      <span className="bnf-claude-strip-text">Claude stopped: {job.error || 'the read failed'}</span>
      <button type="button" className="btn btn-secondary btn-sm" disabled={retry.isPending} onClick={again}>
        ↻ Try again
      </button>
      <button type="button" className="bnf-claude-strip-x" aria-label="Dismiss" onClick={onDismiss}>
        ✕
      </button>
    </div>
  );
}

export default function DrawerNews({ dealId, state, meta, onDocuments, dismissed, retryFor, files }) {
  const navigate = useNavigate();
  const shown = (id) => !dismissed.includes(id);
  const reads = (state.recent || []).filter((job) => job.kind === 'read' && shown(job.id));
  const over = reads.filter((job) => job.land === 'budget' && job.status === 'done');
  const failed = reads.filter((job) => job.status === 'failed');
  const landed = (state.news || []).filter((row) => row.type === 'landed' && shown(row.job_id));
  const waiting = state.waiting || [];
  const nameOf = (id) => files.find((file) => file.id === id)?.display_name || '';
  const open = (docId, page) => navigate(`/deals/${dealId}/documents?doc=${docId}${page ? `&page=${page}` : ''}`);

  return (
    <>
      {(state.jobs || []).map((job) => (
        <RunningCard key={job.id} dealId={dealId} job={job} meta={meta} />
      ))}
      {over.map((job) => (
        <OverBudget
          key={job.id}
          dealId={dealId}
          job={job}
          canOverride={Boolean(state.can?.opus)}
          onDismiss={() => claudeDoor.dismiss(job.id)}
        />
      ))}
      {failed.map((job) => (
        <Failed key={job.id} dealId={dealId} job={job} onDismiss={() => claudeDoor.dismiss(job.id)} />
      ))}
      {!onDocuments &&
        landed.map((row) => (
          <LandedStrip
            key={row.job_id}
            dealId={dealId}
            news={row}
            retry={retryFor(row)}
            onDismiss={() => claudeDoor.dismiss(row.job_id)}
          />
        ))}
      {onDocuments && waiting.length > 0 && (
        <div className="bnf-scanchat-staged-note">
          ⚖ {waiting.length === 1 ? 'A read is' : `${waiting.length} reads are`} waiting for review — open under
          {waiting.length === 1 ? ' its file' : ' their files'} on this tab.
        </div>
      )}
      {!onDocuments &&
        waiting.map((row) => (
          <ReviewCard
            key={row.job_id}
            dealId={dealId}
            jobId={row.job_id}
            renderer={RENDERERS[row.target]}
            meta={meta}
            nameOf={nameOf}
            onOpen={open}
          />
        ))}
    </>
  );
}
