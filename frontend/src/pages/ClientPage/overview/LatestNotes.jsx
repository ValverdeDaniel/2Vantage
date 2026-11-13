import { Link } from 'react-router';
import { useNotes } from '../../../api/notes';
import { formatDate } from '../../../lib/format';
import { clientPath } from '../clientTabs';

const SHOWN = 3;
const CUT = 160; // the old card's cut of a note's body
const MORE = { marginTop: 8 }; // the old card's own spacing above Open Notes →

/**
 * Latest notes (plan.md §8.5; CL22; old ClientOverviewTab.jsx at 891f1b3): the three newest notes of the deal the
 * page works in — the notepad lives on deals — each with its kind and date, and "Open Notes →". Earlier deals' notes
 * wait with renewals (M78). Reads the deal's own notes, the same query its notepad reads.
 */
export default function LatestNotes({ clientId, dealId, inFlight }) {
  const notes = useNotes(dealId);
  const rows = (notes.data || []).slice(0, SHOWN);
  return (
    <div className="bb-panel">
      <div className="bb-panel-title">Latest notes</div>
      <div className="bb-panel-sub">
        {dealId ? `On the ${inFlight ? 'deal in flight' : 'latest deal'}.` : 'The notepad lives on deals.'}
      </div>
      {(!dealId || (notes.isSuccess && rows.length === 0)) && <div className="bb-drop-meta">No notes yet.</div>}
      {rows.map((note) => (
        <div key={note.id} className="bnf-ov-note bnf-cw-note-mini">
          <div className="bnf-ov-note-head">
            <span className={`bb-badge bnf-ov-note-kind bnf-ov-kind-${note.kind}`}>{note.kind_label}</span>
            <span className="bb-drop-meta">{formatDate(note.created_at)}</span>
          </div>
          <div className="bnf-ov-note-body">{note.body.length > CUT ? `${note.body.slice(0, CUT)}…` : note.body}</div>
        </div>
      ))}
      <div className="bb-drop-meta" style={MORE}>
        <Link className="bnf-override-link" to={clientPath(clientId, 'notes')}>
          Open Notes →
        </Link>
      </div>
    </div>
  );
}
