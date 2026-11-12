import { Link } from 'react-router';
import { initialsOf } from '../../lib/dealLook';
import { BY_NAME } from './homeParams';

// Cells both home tables share (HomeCells.jsx at 891f1b3): the avatar with the name and its sub-line, the
// Potential deal size (blank until Deal.deal_size, slice 38) and the Client column's sort header.

/** The client's avatar, the name as the link that opens the deal (the old name button's look), and a sub-line (I76). */
export function AccountCell({ name, sub, to }) {
  return (
    <div className="bb-th-account bb-account-cell">
      <div className="bb-avatar" aria-hidden="true">
        {initialsOf(name)}
      </div>
      <div>
        <Link
          to={to}
          className="bb-account-name bnf-wq-namebtn"
          title="Open this deal — see everything on it"
          onClick={(event) => event.stopPropagation()}
        >
          {name}
        </Link>
        <div className="bb-account-sub">{sub}</div>
      </div>
    </div>
  );
}

/** The Potential deal size header (I124). */
export function DealTh() {
  return (
    <div className="bnf-th-deal" title="This deal's estimate, else the client's most recent one.">
      Potential deal size
    </div>
  );
}

/** Potential deal size: "—" until slice 38 adds Deal.deal_size (I124). */
export function DealCell() {
  return <div className="bnf-th-deal bb-mono">—</div>;
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
