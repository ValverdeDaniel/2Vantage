import { Link } from 'react-router';
import cx from '../../../ui/cx';
import { formatWords, rowSub, tickable } from './packetModel';
import { CheckPill, ForCell, RowNotes, Tick } from './RowParts';

/*
 * A census row of the packet grid (plan.md §8.12; K34–K41, K52; old CarriersTab.jsx at 891f1b3): tick, the carrier's
 * census with its name, columns and rows, its format, who it is for, rows, its pill and "Check ▸" to the Census tab's
 * lens, and Download through the check (K51). A second format (Angle's portal CSV) is its own indented row, off on
 * purpose (K40).
 */
export default function CensusRow({ dealId, row, pill, onSet, files }) {
  const fmt = formatWords(row);
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
        <CheckPill pill={pill} />
        {!row.alt_of && (
          <Link
            className="bnf-override-link"
            data-guide={`rfp-check-${row.key}`}
            title="Open this format on the Census tab: its columns, gaps, warnings and first rows"
            to={`/deals/${dealId}/census?lens=${row.lens}`}
          >
            Check ▸
          </Link>
        )}
      </td>
      <td>
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          disabled={!tickable(row) || files.busy === row.key}
          title={tickable(row) ? '' : row.reason}
          onClick={() => files.download(row.key, row.title)}
        >
          {files.busy === row.key ? 'Building…' : 'Download ⬇'}
        </button>
      </td>
    </tr>
  );
}
