import { Link } from 'react-router';
import { initialsOf } from '../../lib/dealLook';
import { formatMoney } from '../../lib/format';
import { BY_NAME } from './homeParams';
import { SortTh } from './QueueCells';

// Cells both home tables share (HomeCells.jsx at 891f1b3): the avatar with the name and its sub-line, the
// Potential deal size, the Client column's sort header; the Archive cells are in ArchiveCells.jsx.

/** The client's avatar, the name as the link that opens the deal (the old name button's look), and a sub-line (I76).
 *  `title` names where it goes (the Clients rows open the client page, slice 67). */
export function AccountCell({ name, sub, to, title = 'Open this deal — see everything on it' }) {
  return (
    <div className="bb-th-account bb-account-cell">
      <div className="bb-avatar" aria-hidden="true">
        {initialsOf(name)}
      </div>
      <div>
        <Link
          to={to}
          className="bb-account-name bnf-wq-namebtn"
          title={title}
          onClick={(event) => event.stopPropagation()}
        >
          {name}
        </Link>
        <div className="bb-account-sub">{sub}</div>
      </div>
    </div>
  );
}

const DEAL_TITLE = "This deal's estimate, else the client's most recent one.";

/** The Potential deal size header (I124); on the work feed's tables it sorts, biggest first (I81). */
export function DealTh({ sort, onSort }) {
  if (onSort) {
    return (
      <SortTh className="bnf-th-deal" sortKey="deal" sort={sort} onSort={onSort} title={DEAL_TITLE}>
        Potential deal size
      </SortTh>
    );
  }
  return (
    <div className="bnf-th-deal" title={DEAL_TITLE}>
      Potential deal size
    </div>
  );
}

/** Potential deal size, typed in the deal's header (I124, M29; OQ49): "$250,000", or "—". */
export function DealCell({ value }) {
  return <div className="bnf-th-deal bb-mono">{formatMoney(value, { empty: '—' })}</div>;
}

/** The Client header (the old SortTh, a header cell that sorts): A→Z, and back to last updated (the server's two
 *  orders). A div, as the old one was, so it keeps the header's type; Enter and Space work too. */
export function ClientSortTh({ ordering, onSort }) {
  const byName = ordering === BY_NAME;
  const toggle = () => onSort(byName ? '' : BY_NAME);
  return (
    <div
      role="button"
      tabIndex={0}
      className="bb-th-account bnf-th-sortable"
      aria-label={byName ? 'Client, sorted A to Z. Sort by last updated' : 'Client. Sort A to Z'}
      onClick={toggle}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          toggle();
        }
      }}
    >
      Client{byName ? ' ▲' : ''}
    </div>
  );
}
