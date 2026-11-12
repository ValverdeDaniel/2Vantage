import cx from '../../ui/cx';
import { BUILT, LATER, VIEWS, pillLabel } from './reviewModel';

/*
 * The Review tab's View row (L1; old 891f1b3 `DealReviewTab.jsx` VIEW_PILLS, `bnf-advisor-views bnf-board-views`):
 * Board · Request · N to send · Review · N, the counts from the tab's own payload (O.6 #3). Review is greyed at 0 as
 * the old row did, and until its queue is built (slice 55).
 */
export default function ReviewViews({ view, counts, onPick }) {
  return (
    <div className="bnf-advisor-views bnf-board-views" role="group" aria-label="View">
      <span className="bnf-advisor-views-label">View</span>
      {VIEWS.map((v) => {
        const on = v.key === view;
        const built = BUILT.has(v.key);
        const empty = v.key === 'queue' && !counts?.to_review;
        let title = v.title;
        if (empty) title = 'Nothing came back to review';
        else if (!built) title = `${v.title} — ${LATER}`;
        return (
          <button
            key={v.key}
            type="button"
            className={cx('bnf-viewtab', on && 'bnf-viewtab-on')}
            aria-pressed={on}
            disabled={!built || empty}
            title={title}
            onClick={() => {
              if (!on) onPick(v.key);
            }}
          >
            {pillLabel(v.key, counts)}
          </button>
        );
      })}
    </div>
  );
}
