import { KEEP_EDITOR } from '../../../grid/useGridKeys';
import cx from '../../../ui/cx';
import SourcePin from '../../../viewer/SourcePin';
import { FieldValue } from './cells';

/*
 * One plan value on the board (plan.md §8.14, §8.21; F62–F64, F68–F71, E18). The board colours only warnings (the
 * old Advisor): a value to review amber (OQ28: Claude doubted it, or the file does not print it), one flagged ⚑,
 * ignored or approved in its own colour, from the compact cell's flags (`s` status, `m` mark; slice 17). A value
 * read from a file wears ↗ on hover, slice 15's SourcePin with the value's `ref` ("plan:41:rate_ee"), held off the editor's focus so a click on it never saves a stray key (KEEP_EDITOR). In ✎ Edit
 * the cell is on the keyboard grid; outside it a double-click asks to enter Edit (F72). A failed save shows the
 * server's message here, and the cell is back to its last saved value.
 */

const MARK_CLASS = { check: 'bb-cell-check', ignored: 'bb-cell-ignored', approved: 'bb-cell-approved' };
const MARK_TITLE = {
  check: 'Needs checking — someone flagged this value',
  ignored: 'Warning ignored — the value stays as read',
  approved: 'Approved — a person checked this value',
};

function markClass(cell) {
  if (!cell) return '';
  if (MARK_CLASS[cell.m]) return MARK_CLASS[cell.m];
  return cell.s === 'to_check' ? 'bb-cell-low' : '';
}

function markTitle(cell) {
  if (!cell) return undefined;
  if (MARK_TITLE[cell.m]) return MARK_TITLE[cell.m];
  return cell.s === 'to_check' ? 'To review — the reader was unsure of this value, or the file does not print it' : undefined;
}

export default function FieldCell({ plan, col, ui, r, c, clip = false, className, hover }) {
  const cell = plan.cells?.[col.key];
  const doc = cell?.d != null ? ui.documents?.[cell.d] : null;
  const error = ui.errorOf(`${plan.id}|${col.key}`);
  const editor = ui.editing ? ui.grid.editorFor(r, c) : null;
  const gridProps = ui.editing ? ui.grid.cellProps(r, c) : { onDoubleClick: (event) => ui.prompt.ask(event, r, c) };
  const value = <FieldValue col={col} plan={plan} />;
  return (
    <td
      className={cx(
        className,
        col.numeric && 'bb-mono',
        markClass(cell),
        doc && 'bnf-has-src',
        ui.editing && ui.grid.isSelected(r, c) && 'gk-cursor',
        error && 'bnf-cell-error',
      )}
      title={markTitle(cell)}
      data-plan-id={clip ? plan.id : undefined}
      {...hover}
      {...gridProps}
    >
      {editor ? (
        <input className="bnf-conc-cell-input" aria-label={`${col.label} — ${plan.name}`} {...editor} />
      ) : clip ? (
        <div className="bnf-clip">{value}</div>
      ) : (
        value
      )}
      {doc && <SourcePin docId={doc.id} valueRef={`plan:${plan.id}:${col.key}`} fileName={doc.name} {...KEEP_EDITOR} />}
      {error && (
        <em className="bnf-saved-error" role="alert">
          ⚠ {error}
        </em>
      )}
    </td>
  );
}
