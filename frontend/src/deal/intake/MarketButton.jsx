import { useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { invalidateDeal, revertActivity } from '../../api/deals';
import { useMarkMarketed } from '../../api/intake';
import { errorText } from '../../lib/errors';
import ConfirmDialog from '../../ui/ConfirmDialog';
import { useToast } from '../../ui/useToast';

/*
 * The Intake head's ready badge and its button (plan.md §8.9; B10, B33, B34), in the old words and classes (891f1b3
 * `IntakeTab.jsx`, READY_META): "Blocked — required items open" with Market anyway ▸, "Ready to market" with Mark as
 * marketed, "Sent to market" with neither. The server says the state and its words; a 409 names the gaps, and Market
 * anyway asks first, then sends with `override` — the skipped items are recorded in Activity (B34's fix) and the
 * toast offers Undo (Revert of that row). Marking moves no stage (OQ52).
 */
const BADGE_CLASSES = { blocked: 'bnf-ready-blocked', ready: 'bnf-ready-ready', submitted: 'bnf-ready-submitted' };

export function ReadyBadge({ ready }) {
  if (!ready) return null;
  return <span className={`bnf-ready-badge ${BADGE_CLASSES[ready.state] || BADGE_CLASSES.blocked}`}>{ready.label}</span>;
}

function confirmWords(gaps) {
  const count = gaps.length;
  const labels = gaps.map((gap) => gap.label).join(' · ');
  return `${count} item${count === 1 ? '' : 's'} still open: ${labels}. Send to market anyway? What was skipped is recorded in the deal's Activity.`;
}

export default function MarketButton({ deal, ready }) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const mark = useMarkMarketed(deal.id);
  const [gaps, setGaps] = useState(null); // the 409's gaps while "Send to market anyway?" is open
  if (!ready || ready.state === 'submitted') return null;

  async function undo(activityId) {
    try {
      await revertActivity(activityId);
      toast.success('Undone — not sent to market');
    } catch (error) {
      toast.error(errorText(error));
    }
    invalidateDeal(queryClient, deal.id);
  }

  function send(override) {
    mark.mutate(
      { override },
      {
        onSuccess: (answer) => {
          setGaps(null);
          if (!answer.activity_id) return;
          const words = answer.skipped?.length ? 'Marked as sent to market anyway' : 'Marked as sent to market';
          toast.success(
            <span>
              {words} ·{' '}
              <button type="button" className="bnf-linklike" onClick={() => undo(answer.activity_id)}>
                Undo
              </button>
            </span>,
            { duration: 10000 },
          );
        },
        onError: (error) => {
          const body = error?.response?.data;
          if (error?.response?.status === 409 && Array.isArray(body?.gaps)) {
            setGaps(body.gaps);
            return;
          }
          setGaps(null);
          toast.error(errorText(error, { fallback: 'Could not mark the deal as marketed.' }));
        },
      },
    );
  }

  const isReady = ready.state === 'ready';
  return (
    <>
      <button
        type="button"
        className={isReady ? 'btn btn-primary btn-sm' : 'btn btn-secondary btn-sm'}
        title={isReady ? undefined : 'Send to market before the readiness checklist is complete'}
        disabled={mark.isPending}
        onClick={() => send(false)}
      >
        {isReady ? 'Mark as marketed' : 'Market anyway ▸'}
      </button>
      <ConfirmDialog
        open={Boolean(gaps)}
        title="Send to market anyway?"
        message={gaps ? confirmWords(gaps) : ''}
        confirmLabel="Market anyway"
        busy={mark.isPending}
        onCancel={() => setGaps(null)}
        onConfirm={() => send(true)}
      />
    </>
  );
}
