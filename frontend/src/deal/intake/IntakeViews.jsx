import cx from '../../ui/cx';
import { BUILT, LATER, VIEWS } from './views';

/*
 * The Intake tab's view pills, Form · Board · Request · Review (plan.md §8.9; B36), in the old row (891f1b3
 * `SectionViews.jsx` `SectionViewRow`, `bnf-advisor-views`; views.js holds the list). Board, Request and Review come
 * with the Review app (Part L); until then their pills are drawn but cannot be picked, and say when they arrive.
 */
export default function IntakeViews({ view, onPick }) {
  return (
    <div className="bnf-advisor-views" role="group" aria-label="View">
      <span className="bnf-advisor-views-label">View</span>
      {VIEWS.map((v) => {
        const built = BUILT.has(v.key);
        return (
          <button
            key={v.key}
            type="button"
            className={cx('bnf-viewtab', v.key === view && 'bnf-viewtab-on')}
            aria-pressed={v.key === view}
            disabled={!built}
            title={built ? v.title : `${v.title} — ${LATER}`}
            onClick={() => onPick(v.key)}
          >
            {v.label}
          </button>
        );
      })}
    </div>
  );
}
