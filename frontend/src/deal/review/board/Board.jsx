import { labelIn } from '../reviewModel';
import ToReviewLane from './ToReviewLane';
import WaitingLane from './WaitingLane';

const READY_CLASSES = { blocked: 'bnf-ready-blocked', ready: 'bnf-ready-ready', submitted: 'bnf-ready-submitted' };

/*
 * The Board (plan.md §8.8; L2, L7; old 891f1b3 `DealReviewTab.jsx` board view): the head with the deal's intake
 * readiness — its chip, bar and "% intake complete", as the Overview shows it — then the lanes. Slice 53 builds the
 * Waiting lane, slice 55 the To review lane (L9); the Next banner, the client's questions and Missing arrive with
 * slices 56–57. On a deal that may no longer ask its client, the banner says why and the cards only read (L129).
 */
export default function Board({ board, meta, actions, onQueue }) {
  const { readiness } = board;
  return (
    <div className="bnf-board">
      <div className="bnf-board-head">
        <div>
          <div className="bb-tab-title">Review &amp; requests</div>
          <div className="bb-subtitle">Everything this deal is missing, waiting on and has to review, in one place.</div>
        </div>
        <div className="bnf-board-ready" title="Intake readiness, as the Overview shows it">
          <span className={`bnf-ready-badge bnf-ready-badge-sm ${READY_CLASSES[readiness.state] || READY_CLASSES.blocked}`}>
            {labelIn(meta?.readiness, readiness.state)}
          </span>
          <span className="bnf-board-ready-bar" aria-hidden="true">
            <i style={{ width: `${Math.max(0, Math.min(100, readiness.pct))}%` }} />
          </span>
          <b className="bnf-board-ready-pct">{readiness.pct}%</b>
          <span className="bnf-review-note">intake complete</span>
        </div>
      </div>
      {board.asks_closed && <div className="bb-banner">{board.asks_closed}</div>}
      <div className="bnf-board-lanes">
        <WaitingLane board={board} meta={meta} actions={actions} />
        <ToReviewLane dealId={board.deal_id} board={board} onQueue={onQueue} />
      </div>
    </div>
  );
}
