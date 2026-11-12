import cx from '../../../ui/cx';
import { DerivedValue, StarButton, TickBox } from './cells';
import FieldCell from './FieldCell';
import HeadCell from './HeadCell';
import PlanCell from './PlanCell';

/*
 * The board with plans as rows (plan.md §8.14; F31, F40, F57, F62; the old `bnf-advisor-table`): the current plans
 * pinned first, then the quotes in the sort's order. Above 150 plans only the rows in view are drawn, between two
 * pads that keep the scrollbar honest (`win`, useWindowed). In ✎ Edit every value is on the keyboard grid
 * (row = plan id, column = field key).
 */
export default function RowsTable({ board, drawn, ui, win, bodyRef }) {
  const cols = board.columns;
  const pad = (height, key) =>
    height > 0 ? (
      <tr key={key} className="bnf-win-pad" aria-hidden="true" style={{ height }}>
        <td colSpan={cols.length} />
      </tr>
    ) : null;
  return (
    <table className={cx('bnf-advisor-table', ui.editing && 'bnf-advisor-gridmode')}>
      <thead>
        <tr>
          {cols.map((col) => (
            <HeadCell key={col.key} col={col} ui={ui} />
          ))}
        </tr>
      </thead>
      <tbody ref={bodyRef}>
        {pad(win.before, 'pad-before')}
        {win.slice(drawn).map((plan) => (
          <tr key={plan.id} className={plan.role === 'current' ? 'bnf-plan-col-current' : undefined} data-plan-id={plan.id}>
            {cols.map((col) => {
              if (col.kind === 'field') return <FieldCell key={col.key} plan={plan} col={col} ui={ui} r={plan.id} c={col.key} />;
              let content = null;
              if (col.kind === 'select') {
                content = (
                  <TickBox
                    plan={plan}
                    checked={ui.ticks.ids.has(plan.id)}
                    blocked={ui.ticks.block(plan)}
                    hint={ui.ticks.hint(plan)}
                    onToggle={ui.ticks.toggle}
                  />
                );
              } else if (col.kind === 'star') {
                content = <StarButton plan={plan} busy={ui.starring} onToggle={ui.actions.toggleStar} />;
              } else if (col.kind === 'plan') {
                content = <PlanCell plan={plan} board={board} ui={ui} />;
              } else {
                content = <DerivedValue col={col} plan={plan} />;
              }
              return (
                <td key={col.key} className={col.numeric ? 'bb-mono' : undefined}>
                  {content}
                </td>
              );
            })}
          </tr>
        ))}
        {pad(win.after, 'pad-after')}
        {ui.emptyNote && (
          <tr>
            <td colSpan={cols.length} className="bb-empty bnf-nofilter-row">
              {ui.emptyNote}
            </td>
          </tr>
        )}
      </tbody>
    </table>
  );
}
