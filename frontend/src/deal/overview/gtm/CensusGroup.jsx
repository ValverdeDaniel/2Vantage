import { Link } from 'react-router';
import AskButton from '../../shared/AskButton';
import { tabLink } from './gtmModel';

/**
 * Census (M48, M49, M67, M110; old 891f1b3 `GetToMarketCard.jsx`): the roster's people, the required cells filled,
 * the errors to fix, the client's census values waiting with Review ▸, the enrollment check's one warning when intake,
 * the census and the Advisor disagree, the typed-counts notice while the Advisor is priced without a census, then Open
 * census ▸ and the ask: with people on the roster, "＋ Ask ▸" opens the census's Missing lane, person by person; with
 * none, "＋ Ask for their census file" puts the file in review's request tray. No ask once the deal asks its client
 * nothing (`client_asks_open`).
 */
export default function CensusGroup({ dealId, group }) {
  const { employees, dependents } = group;
  return (
    <>
      <div className="bnf-req-line">
        {employees > 0 ? <span className="bb-check">✓</span> : <span className="bb-badge bb-badge-rose">Missing</span>}
        {employees > 0
          ? `${employees} employees + ${dependents} dependents on the roster`
          : 'No employees on the roster yet'}
      </div>
      {group.typed_counts && <div className="bnf-req-detail">{group.typed_counts}</div>}
      {group.required_total > 0 && (
        <div className="bnf-req-line">
          {group.required_filled === group.required_total ? (
            <span className="bb-check">✓</span>
          ) : (
            <span className="bb-badge bb-badge-amber">Open</span>
          )}
          {group.required_filled}/{group.required_total} required cells filled
        </div>
      )}
      {group.errors > 0 && (
        <div className="bnf-req-line">
          <span className="bb-badge bb-badge-rose">{group.errors}</span>
          validation error{group.errors === 1 ? '' : 's'} to fix
        </div>
      )}
      {group.pending_client > 0 && (
        <div className="bnf-req-line">
          <span className="bb-badge bb-badge-violet">Client</span>
          {group.pending_client} census value{group.pending_client === 1 ? '' : 's'} from the client to review
          <Link className="bnf-override-link" to={tabLink(dealId, 'review', { section: 'census' })}>
            Review ▸
          </Link>
        </div>
      )}
      {group.enrollment_warning && (
        <div className="bnf-req-line">
          <span className="bb-badge bb-badge-amber">Check</span>
          {group.enrollment_warning}
        </div>
      )}
      <div className="bnf-req-actions">
        <Link className="bnf-override-link" to={tabLink(dealId, 'census')}>
          Open census ▸
        </Link>
        {group.ask === 'roster' && (
          <Link
            className="bnf-override-link"
            to={tabLink(dealId, 'review', { section: 'census', lane: 'missing' })}
            title="What is still missing, person by person: tick it and ask the client"
          >
            ＋ Ask ▸
          </Link>
        )}
        {group.ask === 'file' && (
          <AskButton
            dealId={dealId}
            refName="census:file"
            label="＋ Ask for their census file"
            className="bnf-override-link"
            title="Put their census file in the request tray: their link asks them to upload it, any layout"
          />
        )}
      </div>
    </>
  );
}
