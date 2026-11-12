import { Fragment, useState } from 'react';
import { Link } from 'react-router';
import { PEOPLE_EXPORT_PATH, cleanFilters, usePeople, usePersonRecords } from '../../api/commission';
import { formatDate, formatMoney } from '../../lib/format';
import ExportButton from '../../ui/ExportButton';
import InlineError from '../../ui/InlineError';
import SplitChips from '../../ui/SplitChips';

/*
 * By person (plan.md §8.18; H68; 891f1b3 `commissions/ByPersonTab.jsx`, its words and classes): everyone who holds a
 * share, their records, expected share and share of the book, by year; a row opens the records behind it with their
 * own share on each; "book ↗" filters the Book by them; Export gives the pivot and a sheet per person. The own tier
 * sees its own row only (OQ73). Every figure is the server's.
 */
const KIND_LABEL = { producer: 'Producer', partner: 'Partner', house: 'House' };

export default function ByPersonTab({ isAll }) {
  const [year, setYear] = useState('');
  const [openKey, setOpenKey] = useState(null);
  const people = usePeople(year);

  if (people.isError) return <InlineError title="By person" error={people.error} onRetry={() => people.refetch()} />;
  if (!people.data) return <div className="loading">Loading…</div>;
  const rows = people.data.rows;

  return (
    <div>
      <div className="bnf-com-filters">
        <select aria-label="Year" value={year} onChange={(event) => setYear(event.target.value)}>
          <option value="">Any year</option>
          {people.data.years.map((entry) => (
            <option key={entry} value={entry}>
              {entry}
            </option>
          ))}
        </select>
        <span className="bb-drop-meta">
          Each person's expected share of the booked records{isAll ? '' : ' you are on'}. Click a row for the records
          behind it.
        </span>
        <span style={{ marginLeft: 'auto' }}>
          <ExportButton
            path={PEOPLE_EXPORT_PATH}
            params={cleanFilters({ year })}
            fallbackName="commission-by-person.xlsx"
            title="The book split up by person — one summary sheet plus a sheet per person with their records and share"
          />
        </span>
      </div>
      {rows.length === 0 && <div className="bnf-com-empty">Nothing booked yet.</div>}
      {rows.length > 0 && (
        <div className="bb-transfers-card" data-guide="people-table">
          <table className="bnf-com-table">
            <thead>
              <tr>
                <th>Person</th>
                <th>Kind</th>
                <th className="bnf-com-num">Records</th>
                <th className="bnf-com-num">Expected (annual)</th>
                <th className="bnf-com-num">Share of book</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <Fragment key={row.key}>
                  <tr
                    className={`bnf-com-clickable ${openKey === row.key ? 'active' : ''}`}
                    onClick={() => setOpenKey(openKey === row.key ? null : row.key)}
                  >
                    <td>{row.name}</td>
                    <td>
                      <span className={`bnf-com-kind bnf-com-kind-${row.kind}`}>{KIND_LABEL[row.kind] || row.kind}</span>
                    </td>
                    <td className="bnf-com-num">{row.records}</td>
                    <td className="bnf-com-num bb-green">{formatMoney(row.expected, { empty: '—' })}</td>
                    <td className="bnf-com-num">{row.share_of_book != null ? `${row.share_of_book}%` : '—'}</td>
                    <td>
                      {row.party ? (
                        <Link to={`/commissions?party=${row.party}`} onClick={(event) => event.stopPropagation()}>
                          book ↗
                        </Link>
                      ) : null}
                    </td>
                  </tr>
                  {openKey === row.key && (
                    <tr className="bnf-com-subrows">
                      <td colSpan={6}>
                        <PersonRecords personKey={row.key} year={year} isAll={isAll} />
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function PersonRecords({ personKey, year, isAll }) {
  const query = usePersonRecords(personKey, year);
  if (!query.data) return <div className="bb-drop-meta">Loading…</div>;
  return (
    <table className="bnf-com-table bnf-com-subtable">
      <thead>
        <tr>
          <th>Client</th>
          <th>Line</th>
          <th>Carrier</th>
          <th>Effective</th>
          <th className="bnf-com-num">Record expected</th>
          <th className="bnf-com-num">Their share</th>
          <th>Everyone</th>
        </tr>
      </thead>
      <tbody>
        {query.data.rows.map((row) => (
          <tr key={row.id}>
            <td>{row.client_name}</td>
            <td>{row.line_label}</td>
            <td>{row.carrier || '—'}</td>
            <td>{row.effective_date ? formatDate(row.effective_date) : '—'}</td>
            <td className="bnf-com-num">{formatMoney(row.expected, { empty: '—' })}</td>
            <td className="bnf-com-num bb-green">
              {row.mine.pct_label}
              {row.mine.amount != null ? ` · ${formatMoney(row.mine.amount)}` : ''}
            </td>
            <td>
              <SplitChips shares={row.shares} showHouse={isAll} />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
