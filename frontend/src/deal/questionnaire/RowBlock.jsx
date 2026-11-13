import { shownFields, shownValue, slotKey } from './formModel';
import FieldRow from './FieldRow';

/*
 * A repeating block on the paper layout (G36, G43): each row a card with its navy chip ("Plan 2", "Row 3") and Remove
 * while above the block's minimum, then "＋ Add …" while below its maximum. Rows keep their ids, so a removal moves no
 * answer; the chip shows the row's place.
 */
export default function RowBlock(props) {
  const { spec, blockKey, data, draft, onChange, onAddRow, onRemoveRow, disabled, lockedOf, canRemove, footOf } = props;
  const block = spec.blocks[blockKey];
  const rows = data.rows?.[blockKey] || [];
  const onScreen = new Set(data.order);
  const atMax = rows.length >= block.max_rows;
  const atMin = rows.length <= block.min_rows;
  return (
    <div className="bnf-q-block">
      {rows.length === 0 && <p className="bnf-q-empty">Nothing added yet — use “{block.add_label}” below.</p>}
      {rows.map((row) => (
        <div className="bnf-q-row" key={row.id}>
          <div className="bnf-q-rowhead">
            <span className="bnf-q-rowchip">
              {block.row_label} {row.number}
            </span>
            {!disabled && !atMin && (!canRemove || canRemove(row)) && (
              <button type="button" className="bnf-q-remove" onClick={() => onRemoveRow(blockKey, row.id)}>
                Remove
              </button>
            )}
          </div>
          <div className="bnf-q-grid">
            {shownFields(block.fields, onScreen, blockKey, row.id).map((field) => {
              const slot = slotKey(blockKey, row.id, field.key);
              return (
                <FieldRow
                  key={field.key}
                  spec={spec}
                  field={field}
                  slot={slot}
                  data={data}
                  value={shownValue(data, draft, slot)}
                  onChange={onChange}
                  disabled={disabled || Boolean(lockedOf?.(slot))}
                  foot={footOf?.(slot)}
                />
              );
            })}
          </div>
        </div>
      ))}
      {!disabled && (
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          disabled={atMax}
          onClick={() => onAddRow(blockKey)}
          title={atMax ? `At most ${block.max_rows} rows` : ''}
        >
          ＋ {block.add_label}
        </button>
      )}
    </div>
  );
}
