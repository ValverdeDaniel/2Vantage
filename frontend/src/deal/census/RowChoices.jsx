import Select from '../../ui/Select';
import { rowNumbers } from './mapping';

const HEADER_ROWS = 20;
const FIRST_ROWS = 40;

/*
 * Where the people are (plan.md §5.3.2 step 2; C15): the sheet, the header row and the first person's row, which the
 * member may change — a census returned on Warner's own template has its header on row 3 and people from row 7. Laid
 * out as rows of the old mapping table (`bnf-map-*`). A new sheet or header row proposes the mapping again.
 */
export default function RowChoices({ imp, onChange, busy }) {
  const sheets = imp.sheets || [];
  const firstRows = rowNumbers(Math.max(FIRST_ROWS, imp.first_data_row)).filter((n) => n > imp.header_row);
  return (
    <div className="bb-panel">
      <div className="bnf-map-head">
        <div>Where the people are</div>
        <div>What it reads</div>
        <div>Choice</div>
        <div />
      </div>
      <div className="bnf-map-row">
        <div className="bnf-map-source">Sheet</div>
        <div className="bnf-map-samples">
          {sheets.length === 1 ? 'The file has one sheet' : `${sheets.length} sheets in this file`}
        </div>
        <div>
          <Select
            aria-label="Sheet"
            value={imp.sheet_name}
            disabled={busy || sheets.length < 2}
            onChange={(event) => onChange({ sheet_name: event.target.value })}
            options={sheets.map((name) => ({ value: name, label: name }))}
          />
        </div>
        <div />
      </div>
      <div className="bnf-map-row">
        <div className="bnf-map-source">Header row</div>
        <div className="bnf-map-samples bb-mono">
          {(imp.headers || []).filter(Boolean).slice(0, 4).join(' · ') || '—'}
        </div>
        <div>
          <Select
            aria-label="Header row"
            value={imp.header_row}
            disabled={busy}
            onChange={(event) => onChange({ header_row: Number(event.target.value) })}
            options={rowNumbers(Math.max(HEADER_ROWS, imp.header_row)).map((n) => ({ value: n, label: `Row ${n}` }))}
          />
        </div>
        <div />
      </div>
      <div className="bnf-map-row">
        <div className="bnf-map-source">First person&apos;s row</div>
        <div className="bnf-map-samples">
          {imp.rows} row{imp.rows === 1 ? '' : 's'} from here on fill a mapped column
        </div>
        <div>
          <Select
            aria-label="First person's row"
            value={imp.first_data_row}
            disabled={busy}
            onChange={(event) => onChange({ first_data_row: Number(event.target.value) })}
            options={firstRows.map((n) => ({ value: n, label: `Row ${n}` }))}
          />
        </div>
        <div />
      </div>
    </div>
  );
}
