import { displayValue } from '../../../lib/fieldValue';
import cx from '../../../ui/cx';
import { cellAt } from './stationModel';

/*
 * One value on the station's Grid (plan.md §8.16, §8.21; E41, E51, E63, E65–E67): its review colour (⚑ checking,
 * approved, ignored, or amber while Claude's doubt is open; rose when a required value is missing), a dotted underline
 * when it was read from a file — greyer when that is not the file in scope, so F will move the viewer — and none when
 * typed; the blue ring while it is the value the viewer shows; the pick, Find's marks and ✎ Edit's cursor. In ✎ Edit a
 * missing value reads "＋ Add", and a failed save shows the server's sentence under the value.
 */

const MARK_CLASS = { check: 'bb-cell-check', ignored: 'bb-cell-ignored', approved: 'bb-cell-approved' };
const MARK_TITLE = {
  check: 'Needs checking — someone flagged this value',
  ignored: 'Warning ignored — the value stays as read',
  approved: 'Approved — a person checked this value',
};
const STATUS_CLASS = { to_check: 'bb-cell-low', missing: 'bb-cell-missing' };

function title(cell) {
  if (MARK_TITLE[cell.flags.m]) return MARK_TITLE[cell.flags.m];
  if (cell.flags.s === 'to_check') return 'To review — the reader was unsure of this value, or the file does not print it';
  if (cell.doc != null && !cell.here) return `Read from ${cell.docName || 'another file'} — F opens it there`;
  if (cell.flags.p) return 'The file does not print this value where expected: look at it again';
  return undefined;
}

export default function ValueCell({ row, plan, ui }) {
  const r = row.key;
  const c = String(plan.id);
  const cell = cellAt(ui.model, r, c);
  const keys = ui.keys;
  const editor = keys ? keys.editorFor(r, c) : null;
  const error = ui.errorOf(`${plan.id}|${r}`);
  const keyProps = keys ? keys.cellProps(r, c) : {};
  // ✎ Edit: a click puts the cursor on the cell (a second click edits) and shows the value in its file (E65).
  const editClick = ui.editing
    ? {
        onClick: (event) => {
          keyProps.onClick?.(event);
          ui.onEditClick(r, c);
        },
      }
    : {};
  const text = displayValue(row.field, cell.raw);
  return (
    <td
      className={cx(
        'bnf-cell',
        plan.role === 'current' && 'bnf-plan-col-current',
        MARK_CLASS[cell.flags.m] || STATUS_CLASS[cell.flags.s],
        cell.doc != null ? 'bb-cell-provenance' : 'bb-cell-noprov',
        cell.doc != null && !cell.here && 'bnf-cell-elsewhere',
        ui.activeRef === cell.ref && 'bb-cell-active',
        ui.editing && keys?.isSelected(r, c) && 'gk-cursor',
        ui.pick?.isPicked(r, c) && 'gs-picked',
        ui.pick?.isActive(r, c) && 'gs-active',
        ui.find.classes(r, c),
        error && 'bnf-cell-error',
      )}
      title={title(cell)}
      {...keyProps}
      {...editClick}
      {...(ui.pick ? ui.pick.cellProps(r, c) : {})}
      {...ui.find.props(r, c)}
      onMouseEnter={ui.clipTip.show}
      onMouseLeave={ui.clipTip.hide}
    >
      {editor ? (
        <input className="bb-cell-input" aria-label={`${row.label} — ${plan.carrier} ${plan.name}`} {...editor} />
      ) : (
        <span className="bb-cell-text bnf-clip">
          {ui.editing && cell.flags.s === 'missing' ? '＋ Add' : text || '—'}
        </span>
      )}
      {error && (
        <em className="bnf-saved-error" role="alert">
          ⚠ {error}
        </em>
      )}
    </td>
  );
}
