import { useSearchParams } from 'react-router';
import { useMeta } from '../../api/meta';
import { useReviewBoard } from '../../api/review';
import InlineError from '../../ui/InlineError';
import Loading from '../../ui/Loading';
import Board from './board/Board';
import RequestView from './newlink/RequestView';
import QueueView from './queue/QueueView';
import ReviewViews from './ReviewViews';
import { viewOf } from './reviewModel';
import useLinkActions from './useLinkActions';

/*
 * The deal's Review & requests tab (plan.md §8.8; Part L; old 891f1b3 `DealReviewTab.jsx`), slice 53's V1: the View
 * row with the tab's own counts (L1, L28), the Board with the readiness strip (L2) and the Waiting lane (L7, L8), and
 * the Request view with a minimal New link (L40). The view is `?view=` (board by default), written on a click. Slice 55
 * adds the Review view, the keyboard queue of what the client sent (L11, L15–L17, L20; B38, C32), and the To review lane.
 * Slice 56 turns the Request view into the request page (who has a link, the ask list, the request tray going out, each
 * item's thread) and puts the client's open questions on the Board (L5).
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
    if (next !== 'queue') nextParams.delete('section');
    if (next !== 'request') ['pane', 'show'].forEach((key) => nextParams.delete(key));
    setParams(nextParams, { replace: true });
  };

  const pickQueue = (section) => {
    const nextParams = new URLSearchParams(params);
    nextParams.set('view', 'queue');
    if (section) nextParams.set('section', section);
    setParams(nextParams, { replace: true });
  };

  const pickRequest = (pane) => {
    const nextParams = new URLSearchParams(params);
    nextParams.set('view', 'request');
    if (pane && pane !== 'intake') nextParams.set('pane', pane);
    nextParams.delete('section');
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
      {view === 'request' && (
        <RequestView deal={deal} meta={meta} actions={actions} asksClosed={board.data.asks_closed} />
      )}
      {view === 'queue' && <QueueView deal={deal} meta={meta} board={board.data} />}
      {view === 'board' && <Board board={board.data} meta={meta} actions={actions} onQueue={pickQueue} onRequest={pickRequest} />}
    </div>
  );
}
