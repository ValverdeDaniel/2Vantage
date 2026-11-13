import { Link } from 'react-router';
import { tabLink } from './gtmModel';

/**
 * Intake answers (M46; old 891f1b3 `GetToMarketCard.jsx`): each needed question still blank, the HR admin contact,
 * the Broker of Record signature, the client's answers waiting with Review ▸ (their section's board), "Intake complete
 * · N lines to quote" once met, and Open intake ▸. Nothing here writes: the answers are the Intake tab's.
 */
export default function IntakeGroup({ dealId, group }) {
  const lines = group.lines;
  return (
    <>
      {group.missing.map((label) => (
        <div key={label} className="bnf-req-line">
          <span className="bb-badge bb-badge-rose">Missing</span>
          {label}
        </div>
      ))}
      {!group.contacts_ok && (
        <div className="bnf-req-line">
          <span className="bb-badge bb-badge-rose">Missing</span>
          HR admin contact (name + email)
        </div>
      )}
      {!group.bor_on_file && (
        <div className="bnf-req-line">
          <span className="bb-badge bb-badge-amber">Open</span>
          Broker of Record signature
        </div>
      )}
      {group.pending_client > 0 && (
        <div className="bnf-req-line">
          <span className="bb-badge bb-badge-violet">Client</span>
          {group.pending_client} answer{group.pending_client === 1 ? '' : 's'} from the client to review
          <Link className="bnf-override-link" to={tabLink(dealId, 'review', { section: 'intake' })}>
            Review ▸
          </Link>
        </div>
      )}
      {group.met && (
        <div className="bnf-req-line">
          <span className="bb-check">✓</span>
          Intake complete · {lines} line{lines === 1 ? '' : 's'} to quote
        </div>
      )}
      <div className="bnf-req-actions">
        <Link className="bnf-override-link" to={tabLink(dealId, 'intake')}>
          Open intake ▸
        </Link>
      </div>
    </>
  );
}
