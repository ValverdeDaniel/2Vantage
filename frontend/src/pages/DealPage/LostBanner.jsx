import { useReopenDeal } from '../../api/deals';
import { errorText } from '../../lib/errors';
import { formatDate } from '../../lib/format';

/**
 * The old lost banner (M4, `bnf-lost-banner`): "✕ Lost <date> — <reason>" with Reopen deal. It sits in the header
 * strip on every tab until slice 62 moves it to the Overview. A lost deal stays editable; its stage waits for Reopen.
 */
export default function LostBanner({ deal }) {
  const reopen = useReopenDeal(deal.id);
  return (
    <div className="bnf-lost-banner" role="status">
      <span>
        ✕ <strong>Lost</strong>
        {deal.lost_at ? ` ${formatDate(deal.lost_at)}` : ''}
        {' — '}
        {deal.lost_reason || 'no reason recorded'}
        {reopen.isError && <span role="alert"> · {errorText(reopen.error)}</span>}
      </span>
      <button
        type="button"
        className="btn btn-secondary btn-sm"
        disabled={reopen.isPending}
        onClick={() => reopen.mutate()}
      >
        Reopen deal
      </button>
    </div>
  );
}
