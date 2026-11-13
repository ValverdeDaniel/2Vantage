import { useNavigate, useSearchParams } from 'react-router';
import { useMeta } from '../../api/meta';
import { useReviewBoard } from '../../api/review';
import InlineError from '../../ui/InlineError';
import Loading from '../../ui/Loading';
import Board from './board/Board';
import RequestView from './newlink/RequestView';
import QueueView from './queue/QueueView';
import ReviewViews from './ReviewViews';
import { scopeOf, viewOf } from './reviewModel';
import useLinkActions from './useLinkActions';

/*
 * The deal's Review & requests tab (plan.md §8.8; Part L; old 891f1b3 `DealReviewTab.jsx`): the View row with the tab's
 * own counts (L1, L28); the Board (L2–L10), or one section's own Board with `?section=` (L12, L45; slice 57); the
 * Request view — the request page, its Ask card and settings card, a new link (slices 56–57); and the Review view, the
 * keyboard queue of what the client sent (L11, L15–L17, L20; slice 55). The view is `?view=` (board by default), written
 * on a click; a row's `fix` ({tab, view?, section?, pane?}) lands here or on its tab.
 */
export default function ReviewTab({ deal }) {
  const meta = useMeta().data?.review;
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const view = viewOf(params);
  const scope = view === 'board' ? scopeOf(params) : '';
  const board = useReviewBoard(deal.id, scope);
  const actions = useLinkActions(deal.id);

  const write = (change) => {
    const next = new URLSearchParams(params);
    Object.entries(change).forEach(([key, value]) => (value ? next.set(key, value) : next.delete(key)));
    setParams(next, { replace: true });
  };
  const pick = (next) => {
    const clear = { view: next === 'board' ? '' : next, section: '', lane: '' };
    if (next !== 'request') Object.assign(clear, { pane: '', show: '', target: '', settings: '', edit: '' });
    write(clear);
  };
  const pickQueue = (section) => write({ view: 'queue', section: section || '' });
  const pickRequest = (pane) => write({ view: 'request', pane: pane && pane !== 'intake' ? pane : '', section: '' });
  const go = (fix) => {
    if (!fix) return;
    if (fix.tab !== 'review') {
      navigate(`/deals/${deal.id}/${fix.tab}`);
      return;
    }
    if (fix.view === 'queue') pickQueue(fix.section);
    else if (fix.view === 'request') pickRequest(fix.pane);
    else write({ view: '', section: fix.section || '', lane: fix.lane || '' });
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
        <RequestView deal={deal} meta={meta} actions={actions} asksClosed={board.data.asks_closed} next={board.data.next} onGo={go} />
      )}
      {view === 'queue' && <QueueView deal={deal} meta={meta} board={board.data} />}
      {view === 'board' && (
        <Board
          board={board.data}
          meta={meta}
          actions={actions}
          scope={scope}
          onQueue={pickQueue}
          onRequest={pickRequest}
          onGo={go}
          lane={params.get('lane') || ''}
          onScope={(section) => write({ section, lane: '' })}
        />
      )}
    </div>
  );
}
