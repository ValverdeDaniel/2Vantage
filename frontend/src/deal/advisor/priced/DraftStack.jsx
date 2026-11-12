import cx from '../../../ui/cx';
import { DraftCell, DraftPlanCell, FormulaCell } from './DraftCells';
import { formulaLabel } from './stack';

/*
 * Where the draft's "Excel stack" goes on the board (plan.md §8.14; F76; the old AdvisorTab tables): with plans as
 * rows, a blue row and a violet draft row under each plan the draft prices; transposed, a blue column and a violet
 * draft column right of it. The source plan itself goes pink (`bnf-pv-source`). The tables call these; a board with
 * no draft draws nothing extra.
 */

/** Rows layout: the blue row and the draft row under `plan`, or nothing. */
export function StackRows({ plan, cols, ui }) {
  const kit = ui.priced;
  const shown = kit?.rowFor(plan.id);
  if (!shown) return null;
  return (
    <>
      <tr className="bnf-pv-formularow">
        {cols.map((col) => (
          <td key={col.key}>
            <FormulaCell col={col} kit={kit} />
          </td>
        ))}
      </tr>
      <tr className="bnf-pv-draftrow">
        {cols.map((col) => (
          <td key={col.key} className={col.numeric ? 'bb-mono' : undefined}>
            {col.kind === 'plan' ? (
              <DraftPlanCell plan={shown} kit={kit} />
            ) : (
              <DraftCell col={col} plan={shown} ui={ui} />
            )}
          </td>
        ))}
      </tr>
    </>
  );
}

/** A blue or draft column's header. */
export function StackHead({ entry, ui, sizes }) {
  return (
    <th scope="col" className={entry.formula ? 'bnf-pv-formulacol' : 'bnf-pv-draftcol'}>
      {entry.formula ? (
        <span className="bnf-pv-formula-label">{formulaLabel(ui.priced)}</span>
      ) : (
        <DraftPlanCell plan={entry.draft} kit={ui.priced} />
      )}
      <span {...sizes.colGrip()} />
    </th>
  );
}

/** A blue or draft column's cell on one row of the transposed board. */
export function StackCell({ entry, col, ui, hover }) {
  if (entry.formula) {
    return (
      <td className="bnf-pv-formulacol">
        <FormulaCell col={col} kit={ui.priced} />
      </td>
    );
  }
  return (
    <td className={cx('bnf-pv-draftcol', col.numeric && 'bb-mono')} {...hover}>
      <div className="bnf-clip">
        <DraftCell col={col} plan={entry.draft} ui={ui} />
      </div>
    </td>
  );
}
