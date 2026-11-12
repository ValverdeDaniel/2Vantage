import { useState } from 'react';
import { useUndoRead } from '../../api/ai';
import { errorText } from '../../lib/errors';
import ConfirmDialog from '../../ui/ConfirmDialog';
import { useToast } from '../../ui/useToast';
import { landedText, UNDO_ASK, undoneToast } from './readWords';

/*
 * A read used in the last minutes (plan.md §10.5; D23, D34, D73; the old ClaudeStrip's "✓ N values changed" and the
 * chat's ↶ Undo this run): what it wrote, what it left out and why, and ↶ Undo this run. Undo asks first; when the
 * server refuses because something changed since (409 with `can_force`), it says what and offers "Undo anyway", which
 * leaves those as they are and puts back the rest.
 */
export default function LandedStrip({ dealId, news, onDismiss }) {
  const toast = useToast();
  const undo = useUndoRead(dealId);
  const [asking, setAsking] = useState(null); // null, {force: false}, or {force: true, why}

  async function run(force) {
    try {
      const { undone } = await undo.mutateAsync({ jobId: news.job_id, force });
      setAsking(null);
      toast.success(undoneToast(undone));
    } catch (error) {
      const data = error.response?.data;
      if (!force && error.response?.status === 409 && data?.can_force) {
        setAsking({ force: true, why: data.detail });
        return;
      }
      setAsking(null);
      toast.error(data?.detail || errorText(error));
    }
  }

  return (
    <div className="bnf-claude-strip bnf-claude-strip-news" role="status" data-landed-job={news.job_id}>
      <span className="bnf-claude-strip-text">
        {landedText(news)}
        {news.skipped?.length > 0 && <span className="bnf-claude-strip-line"> — {news.skipped.join(' ')}</span>}
      </span>
      <button
        type="button"
        className="btn btn-secondary btn-sm"
        disabled={undo.isPending}
        onClick={() => setAsking({ force: false })}
        title="Put the deal back to how it was before this read"
      >
        {undo.isPending ? 'Undoing…' : '↶ Undo this run'}
      </button>
      <button type="button" className="bnf-claude-strip-x" aria-label="Dismiss" onClick={onDismiss}>
        ✕
      </button>
      <ConfirmDialog
        open={Boolean(asking)}
        title={asking?.force ? 'Undo anyway?' : 'Undo this run?'}
        message={
          asking?.force
            ? `${asking.why} Undo anyway leaves that as it is and puts back the rest.`
            : UNDO_ASK
        }
        confirmLabel={asking?.force ? 'Undo anyway' : 'Undo this run'}
        busy={undo.isPending}
        onCancel={() => setAsking(null)}
        onConfirm={() => run(Boolean(asking?.force))}
      />
    </div>
  );
}
