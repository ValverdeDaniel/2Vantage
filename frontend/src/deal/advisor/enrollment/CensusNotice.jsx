import { formatDate } from '../../../lib/format';
import { namesOf } from './countsModel';

/*
 * "Priced from the census now · Keep my typed counts" (plan.md §5.5; F91, OQ18): counts typed before the latest census
 * import give way to the census wherever it can price the plan; this names those plans and keeps the typed counts
 * with one click (they are stamped as typed now, so they win until the next import). In the counts card and above the
 * board (the old `bnf-tiersource-note`, where ComparisonGrid said where its counts came from).
 */
export default function CensusNotice({ block, plans, busy, onKeep }) {
  if (!block?.census_now?.length) return null;
  const typed = formatDate(block.typed_at);
  const imported = formatDate(block.census?.imported_at);
  return (
    <div className="bnf-tiersource-note" role="status">
      <span>
        <b>Priced from the census now</b> ·{' '}
        <button type="button" className="bnf-tiersource-link" disabled={busy} onClick={onKeep}>
          Keep my typed counts
        </button>
        <span className="bnf-pc-note">
          {namesOf(plans, block.census_now)}: the counts typed{typed ? ` on ${typed}` : ''} gave way to the census
          imported{imported ? ` on ${imported}` : ''}.
        </span>
      </span>
    </div>
  );
}
