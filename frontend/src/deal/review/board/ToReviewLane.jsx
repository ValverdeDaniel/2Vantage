import { useNavigate } from 'react-router';
import Lane from './Lane';

/*
 * The To review lane (violet; plan.md §8.8; L9; old 891f1b3 `DealReviewTab.jsx`): a card per section with something
 * back from the client — the census's answers and the people they added, the intake's answers, the client's files —
 * each with what it holds and Review ▸, which opens that section's queue here (or the Documents tab for files). The AI
 * reads' counts stay with the Documents station (L10).
 */
export default function ToReviewLane({ dealId, board, onQueue }) {
  const navigate = useNavigate();
  const rows = board.lanes.to_review || [];
  const go = (fix) => {
    if (fix.tab === 'review') onQueue(fix.section);
    else navigate(`/deals/${dealId}/${fix.tab}`);
  };
  return (
    <Lane title="To review" tone="violet" count={board.counts.to_review} empty="Nothing came back to review.">
      {rows.map((row) => (
        <div key={row.key} className="bnf-board-card">
          <div className="bnf-board-card-head">
            <span className="bnf-board-section">{row.section}</span>
            <span className="rr-pill-count">{row.count}</span>
          </div>
          <div className="bnf-board-card-text">{row.label}</div>
          <div className="bnf-board-card-actions">
            <button
              type="button"
              className="bnf-override-link"
              title={row.fix.tab === 'review' ? `Review it here: the review queue, at ${row.section}` : 'Open the Documents tab'}
              onClick={() => go(row.fix)}
            >
              Review ▸
            </button>
          </div>
        </div>
      ))}
    </Lane>
  );
}
