import { LEAD_COL_PX } from '../../../grid/gridSizes';
import cx from '../../../ui/cx';
import PlanHead from './PlanHead';
import ValueCell from './ValueCell';

/*
 * The station's Grid as a table (plan.md §8.16, §8.21; E36–E41; the old DocumentsTab renderProposalGrid): the plans
 * as columns and their fields as rows in bands, on the Proposal's fixed layout — the Benefit column and the plan
 * heads frozen (`bnf-freeze`), plan columns one width and rows one height each, per user, with ↺ Reset sizes (the
 * Proposal's `proposal` sizes, one stored copy, D-166), a value cut at three lines shown whole on hover. Above 40 plans
 * only the plan columns in view are drawn, between pads that hold the rest's width (E39). A plan head picks its
 * column and a label its row (E51). `ui` carries the model, the hooks' props and the handlers.
 */
export default function GridTable({ view, ui }) {
  const { win, sizes, clipTip } = ui;
  const drawn = win.slice(view.plans);
  const span = drawn.length + 1 + (win.before > 0 ? 1 : 0) + (win.after > 0 ? 1 : 0);
  const padded = (render, Tag) => [
    win.before > 0 ? <Tag key="win-a" className="bnf-win-pad" aria-hidden="true" /> : null,
    ...drawn.map(render),
    win.after > 0 ? <Tag key="win-b" className="bnf-win-pad" aria-hidden="true" /> : null,
  ];
  const hover = { onMouseEnter: clipTip.show, onMouseLeave: clipTip.hide };
  return (
    <div className="bb-grid-card bb-mt bnf-scan-grid">
      <div
        className={cx('bb-grid-scroll gk-grid bnf-freeze', win.on && 'bnf-win-scroll')}
        onScroll={clipTip.hide}
        aria-label="Values read from the file, plans across and benefits down"
        {...ui.containerProps}
      >
        <table
          className={cx('bnf-compare-table bnf-sized', win.on && 'bnf-win-cols')}
          style={sizes.tableStyle(view.plans.length)}
        >
          <colgroup>
            <col style={{ width: LEAD_COL_PX }} />
            {win.before > 0 && <col style={{ width: win.before }} />}
            {drawn.map((plan) => (
              <col key={plan.id} style={{ width: sizes.planCol() }} />
            ))}
            {win.after > 0 && <col style={{ width: win.after }} />}
          </colgroup>
          <thead>
            <tr>
              <th className="bnf-benefit-col">Benefit</th>
              {padded(
                (plan) => (
                  <th
                    key={plan.id}
                    className={cx(
                      plan.role === 'current' ? 'bnf-plan-col-current' : plan.sold && 'bnf-plan-col-sold',
                      ui.find.classes('@head', plan.id),
                    )}
                    {...(ui.pick ? ui.pick.colHeadProps(String(plan.id)) : {})}
                    {...ui.find.props('@head', plan.id)}
                  >
                    <PlanHead
                      plan={plan}
                      issues={ui.model.issues.get(plan.id) ?? 0}
                      renewsName={ui.names.get(plan.renews_id)}
                    />
                    <span {...sizes.colGrip()} />
                  </th>
                ),
                'th',
              )}
            </tr>
          </thead>
          <tbody>
            {view.sections.map((section) => [
              <tr key={`g-${section.group}`} className="bnf-group-row">
                <td colSpan={span}>
                  <span className="bnf-group-label">{section.label}</span>
                </td>
              </tr>,
              ...section.rows.map((row) => (
                <tr key={row.key} style={sizes.rowStyle(row.key)}>
                  <td
                    className={cx('bnf-benefit-col', ui.find.classes(row.key, '@label'))}
                    {...(ui.pick ? ui.pick.rowHeadProps(row.key) : {})}
                    {...ui.find.props(row.key, '@label')}
                    {...hover}
                  >
                    <span className="bnf-clip">{row.label}</span>
                    <span {...sizes.rowGrip(row.key)} />
                  </td>
                  {padded((plan) => <ValueCell key={plan.id} row={row} plan={plan} ui={ui} />, 'td')}
                </tr>
              )),
            ])}
          </tbody>
        </table>
      </div>
    </div>
  );
}
