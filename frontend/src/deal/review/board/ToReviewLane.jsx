import { useNavigate } from 'react-router';
import { fixUrl } from '../section/sectionModel';
import ClientFiles from './ClientFiles';
import Lane from './Lane';

/*
 * The To review lane (violet; plan.md §8.8; L9; old 891f1b3 `DealReviewTab.jsx`): a card per section with something
 * back from the client — the census's answers and the people they added, the intake's answers, the client's files —
 * each with what it holds and Review ▸, which opens that section's queue here (or the Documents tab for files). The AI
 * reads' counts stay with the Documents station (L10). Slice 59: a card per read a client's upload started that waits
 * for a person, "Their census file was read · Review and apply ▸" (L135), opening the census import it staged or the
 * intake read in Work with Claude; the files card lists the files with "Read with Claude ▸" (L125, `ClientFiles`).
 */
export default function ToReviewLane({ dealId, board, readOnly, onQueue }) {
  const navigate = useNavigate();
  const rows = board.lanes.to_review || [];
  const go = (fix) => {
    if (fix.tab === 'review') onQueue(fix.section);
    else navigate(fixUrl(dealId, fix));
  };
  const titleOf = (row) => {
    if (row.action) return 'Open what was read from their file, check it and apply it';
    return row.fix.tab === 'review' ? `Review it here: the review queue, at ${row.section}` : 'Open the Documents tab';
  };
  return (
    <Lane title="To review" tone="violet" count={board.counts.to_review} empty="Nothing came back to review.">
      {rows.map((row) => (
        <div key={row.key} className="bnf-board-card">
          <div className="bnf-board-card-head">
            <span className="bnf-board-section">{row.section}</span>
            <span className="rr-pill-count">{row.count}</span>
          </div>
          <div className="bnf-board-card-text" title={row.detail || undefined}>
            {row.label}
          </div>
          {(row.files || []).length > 0 && (
            <ClientFiles dealId={dealId} files={row.files} more={row.files_more || 0} readOnly={readOnly} />
          )}
          <div className="bnf-board-card-actions">
            <button type="button" className="bnf-override-link" title={titleOf(row)} onClick={() => go(row.fix)}>
              {row.action || 'Review ▸'}
            </button>
          </div>
        </div>
      ))}
    </Lane>
  );
}
