import { useState } from 'react';
import { useDiscardRead, useJob } from '../../api/ai';
import { errorText } from '../../lib/errors';
import Loading from '../../ui/Loading';
import { useToast } from '../../ui/useToast';
import { failedText, leftOutText, summaryLine } from './readWords';

/*
 * "Review this scan" (plan.md §10.5; D28, D31; the old StagedScanReview and ProposedChangesCard): one read's change
 * set, waiting for a person. The head says nothing has changed yet; notes name a stopped or partial read, its failed
 * parts and the pages it did not read; the reader's own body (`renderer`, e.g. the quote reader's plans) shows what
 * would change, each item with its tick; then what the read found worth a look. Discard drops it (D74). Using it —
 * "Use this scan ▸" and "Apply N selected ▸" — lands through the owner's services, which come with slice 19: until
 * then both buttons are shown, disabled, and nothing from a read is written.
 */
const NOT_YET = 'Using a read is not built yet: nothing from it is written.';

export default function ReviewCard({ dealId, jobId, renderer: Body, meta, nameOf }) {
  const toast = useToast();
  const job = useJob(jobId);
  const discard = useDiscardRead(dealId);
  const [picks, setPicks] = useState(null);
  const changeSet = job.data?.result;
  if (job.isPending) return <Loading label="Loading the read…" />;
  if (!changeSet?.items) return null;
  const picked = picks ?? new Set(changeSet.items.filter((item) => item.tick && !item.stale).map((item) => item.id));
  const toggle = (id) =>
    setPicks(() => {
      const next = new Set(picked);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  const words = meta.ai || {};
  const notes = [
    changeSet.partial && !changeSet.failed_parts?.length ? 'Stopped before the end: this is what was read.' : '',
    changeSet.halted || '',
    failedText(changeSet.failed_parts, nameOf, words.failed_words),
    leftOutText(changeSet.left_out_pages, nameOf, words.left_out_words),
  ].filter(Boolean);

  async function drop() {
    try {
      await discard.mutateAsync(jobId);
      toast.success('Read discarded. Nothing on the deal changed.');
    } catch (error) {
      toast.error(errorText(error));
    }
  }

  return (
    <div className="bnf-staged-review bb-mt" data-review-job={jobId}>
      <div className="bnf-staged-head">
        <div>
          <div className="bb-panel-title">Review this scan</div>
          <div className="bb-panel-sub">
            Nothing has changed yet. Compare the new read against what&apos;s on the deal, then keep whichever you
            want. Using this scan never deletes a plan.
          </div>
        </div>
        <div className="bnf-staged-actions">
          <button type="button" className="btn btn-secondary btn-sm" disabled={discard.isPending} onClick={drop}>
            Discard
          </button>
          <button type="button" className="btn btn-secondary btn-sm" disabled title={NOT_YET}>
            Apply {picked.size} selected ▸
          </button>
          <button type="button" className="btn btn-primary btn-sm" disabled title={NOT_YET}>
            Use this scan ▸
          </button>
        </div>
      </div>
      <div className="bnf-staged-summary">{summaryLine(changeSet, words.models)}</div>
      {notes.map((note) => (
        <div key={note} className="bnf-staged-scope-note">
          {note}
        </div>
      ))}
      {Body ? <Body changeSet={changeSet} meta={meta} picked={picked} onToggle={toggle} /> : null}
      {changeSet.findings?.length > 0 && (
        <div className="bnf-staged-section">
          <div className="bnf-staged-section-title">Worth a look</div>
          <ul className="bnf-staged-list">
            {changeSet.findings.map((finding) => (
              <li key={finding.text}>{finding.text}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
