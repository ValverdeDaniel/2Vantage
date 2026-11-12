import { Fragment } from 'react';
import cx from '../../../ui/cx';
import PageColumn from './PageColumn';
import RecommendRow from './RecommendRow';
import { cellText, pageColumns, pageHead, pageSections } from './pageRows';

/*
 * One comparison page as the PowerPoint prints it (plan.md §8.14; F37, F38, J49; the old ProposalPages.jsx page
 * table at 7385bb3): "Page n of N" and the page's words, "x of 6 columns · full", then the plans as columns. The rows:
 * Monthly premium and Change vs current lead, worked out against the "Replacing:" plan by the server; then the
 * Columns tab's rows (or the builder's Key rows), as the client files print them; in the builder, "Our
 * recommendation" (J52). Display only: the documents print every row.
 */
export default function PageTable({ page, count, payload, byId, busy, openId, actions, recommend = null, menu = null }) {
  const columns = pageColumns(page, byId);
  const plans = columns.map((column) => column.plan);
  const head = pageHead(page, count, payload.per_page);
  const tone = (plan) => (plan.kind === 'current' ? 'is-current' : '');
  return (
    <section className="bnf-pg-page" aria-label={head.title}>
      <header className="bnf-pg-pagehead">
        <span>
          <b>{head.title}</b> {head.label}
        </span>
        <span className={cx('bnf-pg-count', page.full && 'is-full')}>{head.count}</span>
      </header>
      <div className="bnf-pg-scroll">
        <table className="bnf-pg-table" style={{ '--pg-cols': plans.length }}>
          <thead>
            <tr>
              <th className="bnf-pg-corner" scope="col">
                Column
              </th>
              {columns.map((column) => (
                <PageColumn
                  key={column.plan.plan_id}
                  column={column}
                  currents={payload.currents}
                  busy={busy}
                  open={openId === column.plan.plan_id}
                  onPick={actions.openPicker}
                  onMove={actions.move}
                  onRemove={actions.remove}
                  onLink={actions.link}
                  menu={menu}
                />
              ))}
            </tr>
          </thead>
          <tbody>
            <tr className="bnf-pg-money">
              <th scope="row">Monthly premium</th>
              {plans.map((plan) => (
                <td key={plan.plan_id} className={tone(plan)}>
                  <span className="bb-mono" title={plan.monthly_note || undefined}>
                    {cellText(plan.monthly)}
                  </span>
                </td>
              ))}
            </tr>
            <tr className="bnf-pg-money">
              <th scope="row">Change vs current</th>
              {plans.map((plan) =>
                plan.kind === 'current' ? (
                  <td key={plan.plan_id} className="is-current">
                    Baseline
                  </td>
                ) : plan.change ? (
                  <td key={plan.plan_id} className={cx('bb-mono', plan.change.up ? 'bnf-delta-pos' : 'bnf-delta-neg')}>
                    {plan.change.text}
                  </td>
                ) : (
                  <td key={plan.plan_id}>—</td>
                ),
              )}
            </tr>
            {pageSections(payload.rows, plans).map((section, s) => (
              <Fragment key={section.heading ?? `rows-${s}`}>
                {section.heading && (
                  <tr className="bnf-pg-section">
                    <th scope="rowgroup" colSpan={plans.length + 1}>
                      {section.heading}
                    </th>
                  </tr>
                )}
                {section.rows.map((row) => (
                  <tr key={row.key}>
                    <th scope="row">{row.label}</th>
                    {row.cells.map((text, i) => (
                      <td key={plans[i].plan_id} className={tone(plans[i])}>
                        {text}
                      </td>
                    ))}
                  </tr>
                ))}
              </Fragment>
            ))}
            {recommend && (
              <RecommendRow
                plans={plans}
                keepable={recommend.keepable}
                disabled={recommend.disabled}
                busy={busy}
                onChoose={actions.recommend}
              />
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
