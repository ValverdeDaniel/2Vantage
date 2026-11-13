import { Link } from 'react-router';
import { ARCHIVED_LINK_TIP } from '../ArchivedPage/archiveCopy';

// Each view's header (A7; plan.md §8.3), in the old home's classes, then its stat cards (A10): the Clients count here;
// Prospects' and the Work queue's cards are StatCards.jsx, on the work feed (slice 61). The Calendar button and card
// wait for the Radar (I88).
const WORDS = {
  prospects: {
    title: 'Prospects',
    subtitle: 'Every prospect once — from intake to the sale — with the one thing each needs next.',
    button: 'New deal',
    card: 'Prospects',
    sub: 'Open prospects, from intake to the sale',
  },
  book: {
    title: 'Clients',
    subtitle:
      'Your persistent book — each client watched year-round for renewal, compliance, and stewardship follow-ups.',
    button: 'New client',
    card: 'Clients',
    sub: null,
  },
  queue: {
    title: 'Work queue',
    subtitle:
      "New deals, renewals, and year-round upkeep in one feed — every row is the next thing a client needs, sorted by when it's due.",
    button: 'New deal',
  },
};

/** The title row with ＋ New deal (Prospects, the Work queue) or Archived and ＋ New client (Clients, as the old book had
 *  them), then the stat cards: `children`, or Clients' count card. */
export default function HomeHeader({ view, count, onCreate, children }) {
  const words = WORDS[view];
  return (
    <>
      <div className="bb-dash-header">
        <div>
          <div className="bb-title" role="heading" aria-level={1}>
            {words.title}
          </div>
          <div className="bb-subtitle">{words.subtitle}</div>
        </div>
        <div className={view === 'book' ? 'bnf-clients-headbtns' : 'bnf-wq-headbtns'}>
          {view === 'book' && (
            <Link className="bnf-archived-link" to="/archived" title={ARCHIVED_LINK_TIP}>
              Archived
            </Link>
          )}
          <button type="button" className="btn btn-primary bb-new-btn" onClick={onCreate}>
            <span className="bb-plus">＋</span> {words.button}
          </button>
        </div>
      </div>
      {children || (
        <div className="bnf-graph-row">
          <div className="bb-stat-card">
            <div className="bb-stat-label">{words.card}</div>
            <div className="bb-stat-value">{count ?? '—'}</div>
            {words.sub && <div className="bb-stat-sub">{words.sub}</div>}
          </div>
        </div>
      )}
    </>
  );
}
