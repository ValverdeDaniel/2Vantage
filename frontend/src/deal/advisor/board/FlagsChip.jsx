import { displayValue } from '../../../lib/fieldValue';
import cx from '../../../ui/cx';
import { planCounts } from '../../../valuereview/marksCache';

/*
 * The Flags column's chip (plan.md §8.14; F63; the old AdvisorTab `flags` column): "⚠ N to review · ⚑ k" when the
 * quote has open warnings — values Claude doubted or the locator could not find, or that someone flagged (OQ28) —
 * else "incomplete" when a key field is blank. A click opens its menu: ✓ Approve, Ignore and ⚑ Needs checking for this
 * one quote (Ignore and Needs checking off when every warning is already flagged), and each value to review with
 * "View in document ▸", which opens it in its file on the Documents tab. `ui.review` is useBoardReview's.
 */
export default function FlagsChip({ plan, ui }) {
  const review = ui?.review;
  const { open, check } = planCounts(plan);
  const incomplete = plan.facts?.incomplete;
  if (!review) {
    return <span className="bnf-flag-cell">{open > 0 && <span className="bnf-flag-chip">⚠ {open} to review</span>}</span>;
  }
  const shown = review.menu === plan.id && open > 0;
  const busy = Boolean(review.busy);
  return (
    <span className="bnf-flag-cell">
      {open > 0 && (
        <button
          type="button"
          className={cx('bnf-flag-chip bnf-flag-chip-btn', check > 0 && 'bnf-flag-chip-check')}
          title="Values the reader was unsure of, or that someone flagged — click to approve, ignore or flag this quote's"
          aria-expanded={shown}
          data-flags-plan={plan.id}
          onClick={() => review.toggle(plan.id)}
        >
          ⚠ {open} to review
          {check > 0 && ` · ⚑ ${check}`}
        </button>
      )}
      {open === 0 && incomplete && <span className="bnf-flag-chip">incomplete</span>}
      {shown && (
        <span className="bnf-flag-menu" role="group" aria-label="Review this quote's warnings">
          <button type="button" className="btn btn-primary btn-sm" disabled={busy} onClick={() => review.plan('approve', plan)}>
            ✓ Approve
          </button>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            disabled={busy || open === check}
            onClick={() => review.plan('ignore', plan)}
          >
            Ignore
          </button>
          <button
            type="button"
            className="btn btn-secondary btn-sm bnf-review-btn-check"
            disabled={busy || open === check}
            onClick={() => review.plan('check', plan)}
          >
            ⚑ Needs checking
          </button>
          <span className="bnf-flag-list">
            {review.flagged(plan).map((key) => {
              const field = review.field(key);
              return (
                <span key={key} className="bnf-flag-item">
                  <span className="bnf-flag-item-label">{field?.label ?? key}</span>{' '}
                  <span className="bnf-flag-item-value">{displayValue(field, plan.values?.[key]) || '—'}</span>
                  {plan.cells?.[key]?.d != null && (
                    <button
                      type="button"
                      className="bnf-linklike bnf-flag-item-view"
                      title="Open the document where this was read"
                      onClick={() => review.view(plan, key)}
                    >
                      View in document ▸
                    </button>
                  )}
                </span>
              );
            })}
          </span>
        </span>
      )}
    </span>
  );
}
