/*
 * One lane of the Board (L5–L10; old 891f1b3 `DealReviewTab.jsx` `Lane`): its tone's count badge, its title, and its
 * cards, or a line saying it is empty. Tones: rose (Missing), amber (Waiting), violet (To review).
 */
export default function Lane({ title, tone, count, empty, action = null, children }) {
  return (
    <section className={`bnf-board-lane bnf-board-lane-${tone}`} aria-label={title}>
      <div className="bnf-board-lane-head">
        <span className={`bb-nav-badge bb-nav-badge-${tone}`}>{count}</span>
        <b>{title}</b>
        {action && <span className="bnf-board-lane-action">{action}</span>}
      </div>
      {count === 0 ? <div className="bnf-review-note bnf-board-empty">{empty}</div> : children}
    </section>
  );
}
