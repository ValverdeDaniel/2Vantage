import { KEEP_EDITOR } from '../../grid/useGridKeys';
import cx from '../../ui/cx';
import SourcePin from '../../viewer/SourcePin';
import PersonCell from './PersonCell';
import { cellClass, cellOf, cellText, cellTitle, columnHint } from './rosterModel';

/*
 * The roster grid (plan.md §8.10, §8.21; C1–C7; the old CensusGrid at 891f1b3, its markup and classes): a header row
 * that stays put, the frozen Person column, one row per person (each employee followed by their dependents), every
 * cell coloured by its mark or status and underlined red or amber by validation. In ✎ Edit it is a spreadsheet
 * (`grid`, useGridKeys): click a cell and type, F2 edits, Enter, Tab, arrows, Home/End move, Esc cancels, Delete
 * clears; a coded column suggests its values through a native datalist (still a text input, so a payroll alias can be
 * typed). Outside Edit a double-click asks to enter it, and a value read from a file wears ↗. While picking cells
 * (☑ Select cells) a click picks or drops a cell instead.
 */

const PERSON_PX = 116; // `.bnf-census-person`, and the scroll-padding of `.bnf-census-scroll`
const listId = (field) => `bnf-codes-${field.key}`;

function Cell({ member, field, ui }) {
  const r = String(member.id);
  const c = field.key;
  const ref = `census:${member.id}:${c}`;
  const editor = ui.editing ? ui.grid.editorFor(r, c) : null;
  const error = ui.errorOf(cellOf(member.id, c));
  const doc = member.sources?.[c]?.doc;
  const pinned = doc && !ui.editing && !ui.picking;
  const keys = ui.editing ? ui.grid.cellProps(r, c) : {};
  return (
    <div
      className={cx(
        'bb-cell',
        cellClass(member, c),
        ui.picking && 'bb-cell-selectable',
        ui.picked.has(ref) && 'bb-cell-selected',
        ui.editing && ui.grid.isSelected(r, c) && 'gk-cursor',
        pinned && 'bnf-has-src',
        error && 'bnf-cell-error',
      )}
      style={{ flex: `0 0 ${field.width}px` }}
      title={error || cellTitle(member, field)}
      data-cell={ref}
      {...keys}
      onClick={ui.picking ? () => ui.onPick(ref) : keys.onClick}
      onDoubleClick={ui.editing ? keys.onDoubleClick : (event) => ui.prompt.ask(event, r, c)}
    >
      {editor ? (
        <input
          className="bb-cell-input"
          aria-label={`${field.label}`}
          list={field.choices?.length ? listId(field) : undefined}
          {...editor}
        />
      ) : (
        <span className="bb-cell-text">{cellText(member, field, ui.editing)}</span>
      )}
      {pinned && <SourcePin docId={doc} valueRef={ref} {...KEEP_EDITOR} />}
    </div>
  );
}

export default function RosterGrid({ members, fields, ui, relationships, onAddDependent, onRemove, onAddEmployee }) {
  const minWidth = PERSON_PX + fields.reduce((sum, field) => sum + field.width, 0);
  return (
    <div className={cx('bb-grid-card', !ui.editing && 'bnf-locked')}>
      <div className="bb-grid-scroll bnf-census-scroll gk-grid" {...ui.grid.containerProps}>
        <div style={{ minWidth: `${minWidth}px` }}>
          <div className="bb-col-headers">
            <div className="bb-loc-col bb-loc-header bnf-person-col bnf-census-person">Person</div>
            {fields.map((field) => (
              <div
                key={field.key}
                className="bb-col-header"
                style={{ flex: `0 0 ${field.width}px` }}
                title={columnHint(field) || undefined}
              >
                <span className="bb-col-label">{field.label}</span>
                {field.choices?.length > 0 && (
                  <span className="bnf-col-hint" aria-hidden="true">
                    ⓘ
                  </span>
                )}
              </div>
            ))}
          </div>
          {members.map((member) => (
            <div key={member.id} className={cx('bb-grid-row', member.kind === 'dependent' && 'bnf-dep-row')}>
              <PersonCell
                member={member}
                editing={ui.editing}
                picking={ui.picking}
                relationships={relationships}
                onAddDependent={onAddDependent}
                onRemove={onRemove}
              />
              {fields.map((field) => (
                <Cell key={field.key} member={member} field={field} ui={ui} />
              ))}
            </div>
          ))}
          {fields
            .filter((field) => field.choices?.length)
            .map((field) => (
              <datalist key={field.key} id={listId(field)}>
                {field.choices.map((choice) => (
                  <option key={choice.value} value={choice.value}>
                    {choice.label}
                  </option>
                ))}
              </datalist>
            ))}
          {ui.editing && !ui.picking && (
            <div className="bnf-census-addrow">
              <button type="button" className="btn btn-secondary btn-sm" onClick={onAddEmployee}>
                ＋ Add employee
              </button>
              <span className="bnf-census-addrow-hint">
                Click a cell and type · Tab → · Enter ↓ · arrows move · Esc cancels
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
