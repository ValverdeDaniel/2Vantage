import Badge from '../../ui/Badge';
import cx from '../../ui/cx';

/*
 * The line tabs with their plan counts (plan.md §8.14; F5; the old board header's `bnf-lineswitch`). Shown with two
 * or more lines; switching drops the ticks and the Move-to pick, and is kept per browser. A line the coverage intent
 * keeps off the proposal wears "Off the proposal", its reason in the title (F13; `off` from plans/lines/).
 */
export default function LineTabs({ lines, line, onPick }) {
  if (lines.length < 2) return null;
  return (
    <div className="bnf-advisor-labelrow">
      <span className="bnf-advisor-views-label">Line</span>
      <nav className="bnf-lineswitch" aria-label="Lines of coverage">
        {lines.map((row) => {
          const count = row.current + row.renewal + row.alternate;
          return (
            <button
              key={row.line}
              type="button"
              aria-current={row.line === line ? 'true' : undefined}
              className={cx('bnf-linetab', row.line === line && 'bnf-linetab-on')}
              title={`${row.current} current · ${row.renewal} renewal · ${row.alternate} alternate${
                row.off ? ` · ${row.off_reason}` : ''
              }`}
              onClick={() => onPick(row.line)}
            >
              {row.label}
              <span className="bnf-linetab-count">{count}</span>
              {row.off && <Badge tone="warning">Off the proposal</Badge>}
            </button>
          );
        })}
      </nav>
    </div>
  );
}
