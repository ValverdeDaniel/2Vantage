// Each view's header and stat card (A7, A10; plan.md §8.3), in the old home's classes. Only the cards with real
// numbers today are drawn: the Prospects count and the Clients count. Potential deal size waits for Deal.deal_size
// (slice 38), Client responses for the work feed (slice 61), and the Calendar button and card for the Radar (I88).
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
};

/** The title row with ＋ New deal (Prospects) or ＋ New client (Clients), then the stat card row. */
export default function HomeHeader({ view, count, onCreate }) {
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
          <button type="button" className="btn btn-primary bb-new-btn" onClick={onCreate}>
            <span className="bb-plus">＋</span> {words.button}
          </button>
        </div>
      </div>
      <div className="bnf-graph-row">
        <div className="bb-stat-card">
          <div className="bb-stat-label">{words.card}</div>
          <div className="bb-stat-value">{count ?? '—'}</div>
          {words.sub && <div className="bb-stat-sub">{words.sub}</div>}
        </div>
      </div>
    </>
  );
}
