import { useRetryRead } from '../../api/ai';
import { errorText } from '../../lib/errors';
import { useToast } from '../../ui/useToast';

/*
 * The over-budget card (plan.md §8.17, §10.3; D24, D53; the old ScanChat's `bnf-overbudget`): a read estimated past
 * its cost cap, or past the deal's budget, waited before it called Claude; the card says so in the server's words.
 * An admin or a direct person may Run anyway (the same read again, past the cap); anyone may Dismiss it.
 */
export default function OverBudget({ dealId, job, canOverride, onDismiss }) {
  const toast = useToast();
  const retry = useRetryRead(dealId);

  async function runAnyway() {
    try {
      await retry.mutateAsync({ jobId: job.id, model: job.model, budgetOverride: true });
      onDismiss();
    } catch (error) {
      toast.error(errorText(error));
    }
  }

  return (
    <div className="bnf-msg bnf-msg-system bnf-overbudget" role="alert" data-over-budget={job.id}>
      {job.wait_reason}
      <div className="bnf-overbudget-actions">
        {canOverride && (
          <button type="button" className="btn btn-primary btn-sm" onClick={runAnyway} disabled={retry.isPending}>
            Run anyway
          </button>
        )}
        <button type="button" className="btn btn-secondary btn-sm" onClick={onDismiss}>
          Dismiss
        </button>
      </div>
    </div>
  );
}
