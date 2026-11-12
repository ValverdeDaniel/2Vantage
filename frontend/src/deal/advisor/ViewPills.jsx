import cx from '../../ui/cx';

/*
 * The Advisor's view pills (plan.md §8.14; F1; the old `bnf-advisor-views` row). Shown only where a second view
 * exists, as the old app did, so a pill never opens nothing: while Quote comparison is the only view built, the row
 * stays away.
 */
export default function ViewPills({ views, view, onPick }) {
  if (views.length < 2) return null;
  return (
    <div className="bnf-advisor-views" role="group" aria-label="View">
      <span className="bnf-advisor-views-label">View</span>
      {views.map((v) => (
        <button
          key={v.key}
          type="button"
          className={cx('bnf-viewtab', v.key === view && 'bnf-viewtab-on')}
          aria-pressed={v.key === view}
          title={v.hint}
          onClick={() => onPick(v.key)}
        >
          {v.label}
        </button>
      ))}
    </div>
  );
}
