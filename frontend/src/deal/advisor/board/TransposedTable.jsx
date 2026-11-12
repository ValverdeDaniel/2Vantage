import { LEAD_COL_PX } from '../../../grid/gridSizes';
import cx from '../../../ui/cx';
import { DerivedValue, SelectAllBox, StarButton, TickBox } from './cells';
import FieldCell from './FieldCell';
import PlanCell from './PlanCell';

/*
 * ⇄ Transposed: plans as columns, the preset's columns as rows in the line's groups (plan.md §8.14; F34–F36; the old
 * `bnf-advisor-transposed`). The header row and the label column are frozen (`bnf-freeze` on the scroller,
 * useFreezePanes); plan columns share one width and rows size one at a time, per user (useGridSizes); a value cut at
 * its row's height shows whole on hover (useClipTip). In ✎ Edit every value is on the keyboard grid (row = field
 * key, column = plan id).
 */
export default function TransposedTable({ board, drawn, sections, ui, sizes, clipTip }) {
  const hover = { onMouseEnter: clipTip.show, onMouseLeave: clipTip.hide };
  const span = drawn.length + 1;
  const byKey = Object.fromEntries(board.columns.map((col) => [col.key, col]));
  return (
    <table
      className={cx('bnf-advisor-table bnf-advisor-transposed bnf-sized', ui.editing && 'bnf-advisor-gridmode')}
      style={sizes.tableStyle(drawn.length)}
    >
      <colgroup>
        <col style={{ width: LEAD_COL_PX }} />
        {drawn.map((plan) => (
          <col key={plan.id} style={{ width: sizes.planCol() }} />
        ))}
      </colgroup>
      <thead>
        <tr>
          <th scope="col">
            <span className="bnf-move-corner">
              <SelectAllBox
                ids={ui.ticks.selectable}
                ticked={ui.ticks.ids}
                editing={ui.editing}
                onChange={ui.ticks.setMany}
              />
            </span>
            Benefit
          </th>
          {drawn.map((plan) => (
            <th
              key={plan.id}
              scope="col"
              className={plan.role === 'current' ? 'bnf-plan-col-current' : undefined}
              data-plan-id={plan.id}
            >
              <PlanCell plan={plan} board={board} ui={ui} />
              <StarButton plan={plan} busy={ui.starring} onToggle={ui.actions.toggleStar} />
              <TickBox
                plan={plan}
                checked={ui.ticks.ids.has(plan.id)}
                blocked={ui.ticks.block(plan)}
                hint={ui.ticks.hint(plan)}
                onToggle={ui.ticks.toggle}
              />
              <span {...sizes.colGrip()} />
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {sections.map((section) => [
          section.group ? (
            <tr key={`g-${section.group}`} className="bnf-group-row">
              <td colSpan={span}>
                <span className="bnf-group-label">{section.label}</span>
              </td>
            </tr>
          ) : null,
          ...section.keys
            .filter((key) => byKey[key])
            .map((key) => {
              const col = byKey[key];
              return (
                <tr key={key} style={sizes.rowStyle(key)}>
                  <td className="bnf-transposed-label" {...hover}>
                    <span className="bnf-clip">{col.label}</span>
                    <span {...sizes.rowGrip(key)} />
                  </td>
                  {drawn.map((plan) => {
                    const current = plan.role === 'current' ? 'bnf-plan-col-current' : undefined;
                    if (col.kind === 'field') {
                      return (
                        <FieldCell
                          key={plan.id}
                          plan={plan}
                          col={col}
                          ui={ui}
                          r={key}
                          c={plan.id}
                          clip
                          className={current}
                          hover={hover}
                        />
                      );
                    }
                    return (
                      <td key={plan.id} className={cx(current, col.numeric && 'bb-mono')} data-plan-id={plan.id} {...hover}>
                        <div className="bnf-clip">
                          <DerivedValue col={col} plan={plan} />
                        </div>
                      </td>
                    );
                  })}
                </tr>
              );
            }),
        ])}
        {ui.emptyNote && (
          <tr>
            <td colSpan={span} className="bb-empty bnf-nofilter-row">
              {ui.emptyNote}
            </td>
          </tr>
        )}
      </tbody>
    </table>
  );
}
