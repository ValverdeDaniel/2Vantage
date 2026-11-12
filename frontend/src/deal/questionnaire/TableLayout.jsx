import { optionsFor, shownValue } from './formModel';
import QuestionInput from './QuestionInput';
import { tableRows } from './tableRows';

/*
 * The form laid out as a table (G37): Section / Question / Answer, every question in the Form's order with the same
 * input, the star and the hint; each row labelled the way the carrier numbers it ("Plan 2"), with Remove on its first
 * question, and "＋ Add …" under each block. `data-q-slot` sits on the answer's cell, never its row, so Enter on Remove
 * is still a click. A signed form reads as plain text, a blank one "— not answered".
 */
export default function TableLayout({ spec, data, draft, onChange, onAddRow, onRemoveRow, disabled }) {
  return (
    <table className="bnf-compare-table bnf-q-table">
      <thead>
        <tr>
          <th>Section</th>
          <th>Question</th>
          <th>Answer</th>
        </tr>
      </thead>
      <tbody>
        {tableRows(spec, data).map((entry) => {
          if (entry.addBlock) {
            if (disabled) return null;
            const block = spec.blocks[entry.addBlock];
            const atMax = entry.count >= block.max_rows;
            return (
              <tr key={entry.key}>
                <td className="bnf-q-taddrow" colSpan={3}>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    disabled={atMax}
                    onClick={() => onAddRow(entry.addBlock)}
                    title={atMax ? `At most ${block.max_rows} rows` : ''}
                  >
                    ＋ {block.add_label}
                  </button>
                </td>
              </tr>
            );
          }
          const { field, key } = entry;
          const value = shownValue(data, draft, key);
          const block = entry.block ? spec.blocks[entry.block] : null;
          const removable = !disabled && entry.firstOfRow && (data.rows?.[entry.block]?.length || 0) > block.min_rows;
          return (
            <tr key={key}>
              <td className="bnf-q-tsection">
                {entry.group}
                {removable && (
                  <button
                    type="button"
                    className="bnf-q-remove bnf-q-tremove"
                    onClick={() => onRemoveRow(entry.block, entry.rowId)}
                  >
                    Remove
                  </button>
                )}
              </td>
              <td>
                {field.label}
                {field.required && <span className="bnf-q-req">*</span>}
                {field.hint && <div className="bnf-q-hint">{field.hint}</div>}
              </td>
              {disabled ? (
                <td className={value ? '' : 'bnf-q-tblank'}>{value || '— not answered'}</td>
              ) : (
                <td className="bnf-q-tanswer" data-q-slot={key}>
                  <QuestionInput
                    slot={key}
                    field={field}
                    options={optionsFor(spec, field, data.options?.[key])}
                    value={value}
                    onChange={onChange}
                  />
                </td>
              )}
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
