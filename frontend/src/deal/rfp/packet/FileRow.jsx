import { Link } from 'react-router';
import cx from '../../../ui/cx';
import FormVariants from './FormVariants';
import { formatWords } from './packetModel';
import { CheckPill, ForCell, RowNotes, Tick } from './RowParts';

/*
 * Any packet row that is not a census format (plan.md §8.12; K42–K49; old CarriersTab.jsx `docRow`, the census-form
 * rows and the attachment rows at 891f1b3): the request form with its variant chips, the cover, a questionnaire, the
 * issued proposal, an attachment, or a Warner form with the census inside (download only, with "Check ▸" to the Warner
 * census lens and its 500-row cap). Download goes through the check (K50, K51).
 */
export default function FileRow({ dealId, row, pill, onSet, onForm, files }) {
  const downloadOnly = row.packet_eligible === false;
  return (
    <tr data-guide={`rfp-row-${row.key}`} className={cx(row.include && 'bnf-rfp-row-in')}>
      <td className="bnf-rfp-col-tick">
        <Tick row={row} onSet={onSet} />
      </td>
      <td>
        <div className="bnf-rfp-doc">
          {row.title}
          {row.recommended && <span className="bnf-rfp-chip-tag"> · standard</span>}
        </div>
        {row.sub && <div className="bnf-rfp-sub">{row.sub}</div>}
        {row.options && <FormVariants row={row} onPick={onForm} />}
        {downloadOnly ? (
          <>
            {row.reason && <div className="bnf-rfp-rownote">{row.reason}</div>}
            {row.capped && (
              <div className="bnf-rfp-rownote bb-amber">
                ⚠ The form has room for {row.max_rows} people; the last {row.rows - row.max_rows} are not on it.
              </div>
            )}
          </>
        ) : (
          <RowNotes row={row} />
        )}
      </td>
      <td>
        <span className="bnf-export-fmt bb-mono">{formatWords(row)}</span>
      </td>
      <td>
        <ForCell row={row} />
      </td>
      <td className="bnf-rfp-num">{row.rows ?? '—'}</td>
      <td className="bnf-rfp-num">
        <CheckPill pill={pill} />
        {downloadOnly && row.lens && (
          <Link className="bnf-override-link" to={`/deals/${dealId}/census?lens=${row.lens}`}>
            Check ▸
          </Link>
        )}
      </td>
      <td>
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          disabled={row.available === false || files.busy === row.key}
          title={row.available === false ? row.reason : ''}
          onClick={() => files.download(row.key, row.title)}
        >
          {files.busy === row.key ? 'Building…' : 'Download ⬇'}
        </button>
      </td>
    </tr>
  );
}
