import { useSearchParams } from 'react-router';
import { useMeta } from '../../api/meta';
import { useReviewBoard } from '../../api/review';
import InlineError from '../../ui/InlineError';
import Loading from '../../ui/Loading';
import Board from './board/Board';
import RequestView from './newlink/RequestView';
import ReviewViews from './ReviewViews';
import { viewOf } from './reviewModel';
import useLinkActions from './useLinkActions';

/*
 * The deal's Review & requests tab (plan.md §8.8; Part L; old 891f1b3 `DealReviewTab.jsx`), slice 53's V1: the View
 * row with the tab's own counts (L1, L28), the Board with the readiness strip (L2) and the Waiting lane (L7, L8), and
 * the Request view with a minimal New link (L40). The view is `?view=` (board by default), written on a click.
 */
export default function ReviewTab({ deal }) {
  const meta = useMeta().data?.review;
  const board = useReviewBoard(deal.id);
  const [params, setParams] = useSearchParams();
  const view = viewOf(params);
  const actions = useLinkActions(deal.id);

  const pick = (next) => {
    const nextParams = new URLSearchParams(params);
    if (next === 'board') nextParams.delete('view');
    else nextParams.set('view', next);
    setParams(nextParams, { replace: true });
  };

  if (board.isPending || !meta) return <Loading label="Loading what is open on this deal…" />;
  // A failed refetch keeps what was drawn (a just-made link and its PIN stay on screen); only a first read fails here.
  if (board.isError && !board.data) {
    return <InlineError title="Review & requests" error={board.error} onRetry={() => board.refetch()} retrying={board.isFetching} />;
  }
  return (
    <div className="bb-tab-page">
      <ReviewViews view={view} counts={board.data.counts} onPick={pick} />
      {view === 'request' ? (
        <RequestView deal={deal} meta={meta} actions={actions} onDone={() => pick('board')} asksClosed={board.data.asks_closed} />
      ) : (
        <Board board={board.data} meta={meta} actions={actions} />
      )}
    </div>
  );
}
