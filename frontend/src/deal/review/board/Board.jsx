import { labelIn } from '../reviewModel';
import SectionBoard from '../sections/SectionBoard';
import MissingLane from './MissingLane';
import NextBanner from './NextBanner';
import QuestionsBlock from './QuestionsBlock';
import ToReviewLane from './ToReviewLane';
import WaitingLane from './WaitingLane';

const READY_CLASSES = { blocked: 'bnf-ready-blocked', ready: 'bnf-ready-ready', submitted: 'bnf-ready-submitted' };
const SCOPES = { intake: 'Intake', census: 'Census' };

/*
 * The Board (plan.md §8.8; L2–L10, L12, L45; old 891f1b3 `DealReviewTab.jsx` board view): the head with the deal's
 * intake readiness — its chip, bar and "% intake complete", as the Overview shows it — then Next → (L3, L4), the
 * client's open questions (L5) and the three lanes: Missing (L6), Waiting on the client (L7) and To review (L9).
 * `?section=intake|census` is that section's own Board (L12, L45): its lanes and its Next, "All links ▸" back to the
 * whole deal, and its board of questions or columns (B37, C27, C30), which Missing's Open ▸ and "Every question ▸" open
 * (`?lane=missing`, the old section board's Missing lane). On a deal that may no longer ask its
 * client, the banner says why and the cards only read (L129).
 */
export default function Board({ board, meta, actions, scope, lane, onQueue, onRequest, onGo, onScope }) {
  const { readiness } = board;
  const readOnly = Boolean(board.asks_closed);
  const label = SCOPES[scope];
  return (
    <div className="bnf-board">
      <div className="bnf-board-head">
        <div>
          <div className="bb-tab-title">{label ? `${label} board` : 'Review & requests'}</div>
          <div className="bb-subtitle">
            {label
              ? `What the ${label.toLowerCase()} is missing, waiting on and has to review.`
              : 'Everything this deal is missing, waiting on and has to review, in one place.'}
          </div>
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
      {!scope && (
        <div className="bnf-advisor-views bnf-board-views" role="group" aria-label="Section">
          <span className="bnf-advisor-views-label">Section</span>
          {Object.entries(SCOPES).map(([key, words]) => (
            <button key={key} type="button" className="bnf-viewtab" onClick={() => onScope(key)}
              title={`The ${words.toLowerCase()}'s own board: its questions or columns, what it is missing and asks`}>
              {words} ▸
            </button>
          ))}
        </div>
      )}
      <NextBanner
        key={scope || 'all'}
        entries={board.next}
        kinds={meta?.next_kinds}
        where={label ? `the ${label.toLowerCase()}` : 'this deal'}
        onGo={onGo}
        onExtend={actions.extend}
        readOnly={readOnly}
      />
      {scope && lane === 'missing' ? (
        <>
          <button type="button" className="bnf-override-link" onClick={() => onGo({ tab: 'review', view: 'board', section: scope })}>
            ◂ The {label.toLowerCase()}’s lanes
          </button>
          <SectionBoard dealId={board.deal_id} surface={scope} meta={meta} readOnly={readOnly} />
        </>
      ) : (
        <BoardLanes board={board} meta={meta} actions={actions} scope={scope} label={label} readOnly={readOnly} onGo={onGo}
          onQueue={onQueue} onRequest={onRequest} onScope={onScope} />
      )}
    </div>
  );
}

function BoardLanes({ board, meta, actions, scope, label, readOnly, onGo, onQueue, onRequest, onScope }) {
  return (
    <>
      <QuestionsBlock board={board} onRequest={onRequest} />
      <div className="bnf-board-lanes">
        <MissingLane dealId={board.deal_id} rows={board.lanes.missing} onGo={onGo} readOnly={readOnly} />
        <WaitingLane board={board} meta={meta} actions={actions}
          action={label ? (
            <button type="button" className="bnf-override-link" onClick={() => onScope('')} title="Every link on this deal: the whole Board">
              All links ▸
            </button>
          ) : null} />
        <ToReviewLane dealId={board.deal_id} board={board} onQueue={onQueue} />
      </div>
      {scope && (
        <button type="button" className="bnf-override-link" onClick={() => onGo({ tab: 'review', view: 'board', section: scope, lane: 'missing' })}
          title={scope === 'intake' ? 'Every question, what this deal needs of each, and the note the client reads' : 'Every column, how full it is and where its values came from'}>
          {scope === 'intake' ? 'Every question ▸' : 'Every column ▸'}
        </button>
      )}
    </>
  );
}
