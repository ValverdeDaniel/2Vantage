import { Link } from 'react-router';

/**
 * Coverage notes (plan.md §8.6; M80; old Vantage 891f1b3 `CoverageNotesCard.jsx`): every note written against a
 * coverage line, in the intent card's order, with the line, its carrier and its state; Edit on Intake ▸ opens the
 * card that owns them. Nothing at all when no line carries a note.
 */
export default function CoverageNotesCard({ dealId, notes }) {
  if (!notes?.length) return null;
  return (
    <div className="bb-panel bnf-ov-cvgnotes">
      <div className="bb-panel-title">Coverage notes</div>
      <div className="bb-panel-sub">What we noted against each line — edit them on the coverage card.</div>
      <div className="bnf-ov-cvgnote-list">
        {notes.map((row) => (
          <div key={row.line} className="bnf-ov-cvgnote">
            <div className="bnf-ov-cvgnote-head">
              <span className="bnf-ov-cvgnote-line">{row.label}</span>
              {row.carrier && <span className="bb-drop-meta"> · {row.carrier}</span>}
              {row.state_label && <span className="bb-drop-meta"> · {row.state_label}</span>}
            </div>
            <div className="bnf-ov-cvgnote-body">{row.body}</div>
          </div>
        ))}
      </div>
      <Link className="bnf-override-link" to={`/deals/${dealId}/intake`} title="Open the coverage & marketing intent card">
        Edit on Intake ▸
      </Link>
    </div>
  );
}
