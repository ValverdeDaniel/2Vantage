import { useState } from 'react';
import { useRetryRead, useUndoRead } from '../../api/ai';
import { errorText } from '../../lib/errors';
import ConfirmDialog from '../../ui/ConfirmDialog';
import { useToast } from '../../ui/useToast';
import { landedText, retryAsk, UNDO_ASK, undoneToast } from './readWords';

/*
 * A read used in the last minutes, by a person or by itself (plan.md §10.5; D23, D34, D71, D73, D76; the old
 * ClaudeStrip's "✓ N values changed" and the chat's ↶ Undo this run and ↻ Try again with <next model>): what it
 * wrote, what it left out and why, ↶ Undo this run and, for someone who may use the next model up, ↻ Try again with it
 * (`retry`: {model, label}), which undoes this run and reads the same files again. Both ask first; when the server
 * refuses because something changed since (409 with `can_force`), it says what and offers "Undo anyway", which leaves
 * those as they are and puts back the rest.
 */
export default function LandedStrip({ dealId, news, onDismiss, retry = null }) {
  const toast = useToast();
  const undo = useUndoRead(dealId);
  const again = useRetryRead(dealId);
  const [asking, setAsking] = useState(null); // null, {force: false, retry?}, or {force: true, why, retry?}

  async function run(force) {
    if (asking?.retry) {
      await tryAgain(force);
      return;
    }
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

  async function tryAgain(force) {
    try {
      await again.mutateAsync({ jobId: news.job_id, model: retry.model, force });
      setAsking(null);
      toast.success(`Undone — ${retry.label} is reading the same files again.`);
    } catch (error) {
      const data = error.response?.data;
      if (!force && error.response?.status === 409 && data?.can_force) {
        setAsking({ force: true, why: data.detail, retry: true });
        return;
      }
      setAsking(null);
      toast.error(data?.detail || errorText(error));
    }
  }

  const busy = undo.isPending || again.isPending;

  return (
    <div className="bnf-claude-strip bnf-claude-strip-news" role="status" data-landed-job={news.job_id}>
      <span className="bnf-claude-strip-text">
        {landedText(news)}
        {news.skipped?.length > 0 && <span className="bnf-claude-strip-line"> — {news.skipped.join(' ')}</span>}
      </span>
      <button
        type="button"
        className="btn btn-secondary btn-sm"
        disabled={busy}
        onClick={() => setAsking({ force: false })}
        title="Put the deal back to how it was before this read"
      >
        {undo.isPending ? 'Undoing…' : '↶ Undo this run'}
      </button>
      {retry && (
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          disabled={busy}
          onClick={() => setAsking({ force: false, retry: true })}
          title="Undo this run and read the same files again on the stronger model"
        >
          ↻ Try again with {retry.label}
        </button>
      )}
      <button type="button" className="bnf-claude-strip-x" aria-label="Dismiss" onClick={onDismiss}>
        ✕
      </button>
      <ConfirmDialog
        open={Boolean(asking)}
        title={asking?.force ? 'Undo anyway?' : asking?.retry ? 'Try again?' : 'Undo this run?'}
        message={
          asking?.force
            ? `${asking.why} Undo anyway leaves that as it is and puts back the rest.`
            : asking?.retry
              ? retryAsk(retry.label)
              : UNDO_ASK
        }
        confirmLabel={asking?.force ? 'Undo anyway' : asking?.retry ? `Try again with ${retry.label}` : 'Undo this run'}
        busy={busy}
        onCancel={() => setAsking(null)}
        onConfirm={() => run(Boolean(asking?.force))}
      />
    </div>
  );
}
