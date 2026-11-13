import RequestCard from '../request/RequestCard';
import { runsOutWords, waitingCount } from '../reviewModel';
import Lane from './Lane';

/*
 * Waiting on the client (L7; old 891f1b3 `DealReviewTab.jsx`): who is still answering, then every request still out,
 * the one running out soonest first, each a request card with its chips. Questions open, follow-ups and replies
 * not seen arrive with the threads (slice 56). On a section's own Board, `action` is "All links ▸" (L12).
 */
export default function WaitingLane({ board, meta, actions, action = null }) {
  const readOnly = Boolean(board.asks_closed);
  return (
    <Lane title="Waiting on the client" tone="amber" count={waitingCount(board)} empty="No request is out." action={action}>
      {board.in_progress.map((person) => (
        <div key={`typing:${person.link_id}`} className="bnf-board-card">
          <div className="bnf-board-card-text">
            <b>{person.name || 'Someone with the private link'}</b> is still answering — not submitted yet.
          </div>
        </div>
      ))}
      {board.lanes.waiting.map((request) => (
        <RequestCard key={request.id} request={request} meta={meta} actions={actions} readOnly={readOnly}>
          {request.expiring && (
            <div className="bnf-board-reqfoot">
              <span className="bnf-board-chip bnf-board-chip-warn">{runsOutWords(request.soonest_days)}</span>
            </div>
          )}
        </RequestCard>
      ))}
    </Lane>
  );
}
