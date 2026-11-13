import { Link } from 'react-router';
import { disclosurePath } from '../../../api/commission';
import { downloadFile } from '../../../lib/download';
import { errorText } from '../../../lib/errors';
import { formatMoney } from '../../../lib/format';
import SplitChips from '../../../ui/SplitChips';
import { useToast } from '../../../ui/useToast';
import { changeWords, holeWords, inactive, yearGroups } from './bookView';

const COLUMNS = 6;

function YearHead({ year, below, meta }) {
  const toast = useToast();
  const download = () =>
    downloadFile(disclosurePath(year.deal_id), { fallbackName: 'comp-disclosure.pdf' }).catch((error) =>
      toast.error(errorText(error)),
    );
  const change = changeWords(year, below);
  return (
    <tr className="bnf-com-grouphead">
      <td colSpan={COLUMNS}>
        <strong>Plan year {year.label}</strong>
        {year.disclosure && (
          <button
            type="button"
            className="bnf-override-link"
            style={{ marginLeft: 10 }}
            title={meta.commission?.disclosure_hint}
            onClick={download}
          >
            Comp disclosure ⤓
          </button>
        )}
        {year.holes ? (
          <span className="bb-badge bb-badge-amber" style={{ marginLeft: 8 }}>
            {holeWords(year.holes)}
          </span>
        ) : null}
        <span className="bnf-com-groupsum">
          expected <strong className="bb-green">{formatMoney(year.expected, { empty: '—' })}</strong>
          {change && <span className={`bnf-com-delta ${year.change_pct >= 0 ? 'up' : 'down'}`}> {change}</span>}
        </span>
      </td>
    </tr>
  );
}

function RecordRow({ row, meta }) {
  const rateHole = (row.holes || []).includes('rate');
  return (
    <tr>
      <td>
        {row.line_label || row.line}
        {inactive(row, meta) && <span className="bb-drop-meta"> · {row.status_label}</span>}
        {row.deal_id && (
          <Link
            className="bnf-cw-stmt-case"
            to={`/deals/${row.deal_id}/commission`}
            title="Open the year this booked from"
          >
            {' '}
            year ↗
          </Link>
        )}
      </td>
      <td>{row.carrier || '—'}</td>
      <td className={`bnf-com-num ${row.premium_annual == null ? 'bnf-com-hole' : ''}`}>
        {row.premium_annual != null ? formatMoney(row.premium_annual) : 'not known'}
      </td>
      <td className={rateHole ? 'bnf-com-hole' : ''}>{row.rate_label || 'not set'}</td>
      <td className={`bnf-com-num ${row.expected != null ? 'bb-green' : ''}`}>{formatMoney(row.expected, { empty: '—' })}</td>
      <td className="bnf-cw-stmt-people-cell">
        <SplitChips shares={row.shares} showHouse showMoney />
      </td>
    </tr>
  );
}

/**
 * "Booked, by plan year" (plan.md §8.5; CL25; old 891f1b3 `ClientCommissionsTab.jsx`'s statement table): one head row
 * per plan year (the year, its CAA disclosure for the all tier, its holes, its expected and the change against the
 * year before, all the server's), then a row per booked line: line (and "year ↗" to the deal's Commission tab),
 * carrier, premium, rate, expected and who gets what, in the viewer's tier (the own tier sees its own share only).
 * The twelve-month strip, Rec'd and short figures and the person chips wait with the ledger (OQ6).
 */
export default function BookedByYear({ book, meta }) {
  const groups = yearGroups(book);
  return (
    <div className="bb-panel">
      <div className="bnf-cw-stmt-header">
        <div>
          <div className="bnf-com-section-title" style={{ marginTop: 0 }}>
            Booked, by plan year
          </div>
          <div className="bb-panel-sub">
            Each line as the sale froze it — premium · rate → expected — then who gets what in % and $.
          </div>
        </div>
      </div>
      {groups.length === 0 ? (
        <div className="bb-drop-meta">Nothing booked yet — records are created when a deal is marked sold.</div>
      ) : (
        <div className="bnf-cw-stmt-scroll">
          <table className="bnf-com-table bnf-cw-stmt-table">
            <thead>
              <tr>
                <th>Line</th>
                <th>Carrier</th>
                <th className="bnf-com-num">Premium</th>
                <th>Rate</th>
                <th className="bnf-com-num">Expected</th>
                <th>Who gets what</th>
              </tr>
            </thead>
            <tbody>
              {groups.map((year, index) => (
                <YearRows key={year.key || 'undated'} year={year} below={groups[index + 1]} meta={meta} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function YearRows({ year, below, meta }) {
  return (
    <>
      <YearHead year={year} below={below} meta={meta} />
      {year.rows.map((row) => (
        <RecordRow key={row.id} row={row} meta={meta} />
      ))}
    </>
  );
}
