import { Link } from 'react-router';
import cx from '../../../ui/cx';
import { isPick, rowSub, tickable, tickBody } from './packetModel';

/* One row's tick (K35); a row that cannot be built yet is greyed (K41). */
function Tick({ row, onSet }) {
  const off = !tickable(row);
  return (
    <label
      className={cx('bnf-rfp-include', off && 'bnf-rfp-include-off')}
      data-guide={`rfp-include-${row.key}`}
      title={off ? 'Not ready to build yet' : 'In the packet'}
    >
      <input
        type="checkbox"
        checked={Boolean(row.include)}
        disabled={off}
        aria-label={`${row.carrier} census in the packet`}
        onChange={(event) => onSet(tickBody(row, event.target.checked))}
      />
    </label>
  );
}

/* What a row is and why it stands where it does (K37): "your pick", "Off on purpose — …", "Ticked by hand — …". */
function RowNotes({ row }) {
  return (
    <>
      {isPick(row) && (
        <span
          className="bnf-rfp-pick"
          title="Differs from what the carrier picks recommend — “Recommended” puts it back"
        >
          your pick
        </span>
      )}
      {row.deliberate && (
        <div className="bnf-rfp-rownote bnf-rfp-rownote-deliberate">
          {row.include ? 'Ticked by hand — ' : 'Off on purpose — '}
          {row.deliberate}
        </div>
      )}
      {row.reason && <div className="bnf-rfp-rownote">{row.reason}</div>}
      {row.capped && !row.alt_of && (
        <div className="bnf-rfp-rownote bb-amber">
          ⚠ The file has room for {row.max_rows} people; the last {row.rows - row.max_rows} on the census are not in it.
        </div>
      )}
    </>
  );
}

/* Who a row is for (K36): the picked carriers; Warner's universal census "Any carrier" when nobody is named. */
function ForCell({ row }) {
  if (row.required_by?.length) {
    return (
      <span className="bnf-rfp-for">
        {row.required_by.map((name) => (
          <span key={name} className="bnf-rfp-for-chip">
            {name}
          </span>
        ))}
      </span>
    );
  }
  return <span className="bb-muted">{row.universal && !row.alt_of ? 'Any carrier' : '—'}</span>;
}

/*
 * A census row of the packet grid (plan.md §8.12; K34–K41; old CarriersTab.jsx at 891f1b3): tick, the carrier's
 * census with its name, columns and rows, its format, who it is for, rows, "Check ▸" to the Census tab's lens, and
 * Download. A second format (Angle's portal CSV) is its own indented row, off on purpose (K40).
 */
export default function CensusRow({ dealId, row, onSet, onDownload, downloading }) {
  const fmt = (row.file_format || 'xlsx').toUpperCase();
  const lensKey = row.alt_of || row.key;
  return (
    <tr
      data-guide={`rfp-row-${row.key}`}
      className={cx(row.alt_of && 'bnf-rfp-row-alt', row.include && 'bnf-rfp-row-in')}
    >
      <td className="bnf-rfp-col-tick">
        <Tick row={row} onSet={onSet} />
      </td>
      <td>
        <div className="bnf-rfp-doc">{row.alt_of ? `↳ ${fmt} for their portal` : `${row.carrier} census`}</div>
        {!row.alt_of && <div className="bnf-rfp-sub">{rowSub(row)}</div>}
        <RowNotes row={row} />
      </td>
      <td>
        <span className="bnf-export-fmt bb-mono">{fmt}</span>
      </td>
      <td>
        <ForCell row={row} />
      </td>
      <td className="bnf-rfp-num">{row.rows}</td>
      <td className="bnf-rfp-num">
        {row.alt_of ? (
          '—'
        ) : (
          <Link
            className="bnf-override-link"
            data-guide={`rfp-check-${row.key}`}
            title="Open this format on the Census tab: its columns, gaps, warnings and first rows"
            to={`/deals/${dealId}/census?lens=${lensKey}`}
          >
            Check ▸
          </Link>
        )}
      </td>
      <td>
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          disabled={!tickable(row) || downloading}
          title={tickable(row) ? '' : row.reason}
          onClick={() => onDownload(row)}
        >
          {downloading ? 'Building…' : 'Download ⬇'}
        </button>
      </td>
    </tr>
  );
}
