import { useMeta } from '../../api/meta';
import { formatDate, formatMoney } from '../../lib/format';
import CompInput from '../../deal/shared/CompInput';
import FactRow from './FactRow';

/*
 * A record's facts (H54; 891f1b3 `commissions/RecordDrawer.jsx`'s grid, its words): premium as billed, the carrier
 * rate (CompInput), carrier, policy number, effective date, term end, enrolled (for PEPM), status and the year. The
 * all tier types any of them (a typed fact is never changed by a booking again); everyone else reads them. Each fact's
 * origin shows under its label ("from the sale", "entered by hand", …).
 */
export default function RecordFacts({ record, isAll, onSave }) {
  const meta = useMeta().data;
  const words = meta?.commission?.record_sources || {};
  const origin = (key) => words[record.sources[key]] || '';
  const year = record.year_number ? (record.year_number === 1 ? 'First year' : `Renewal, year ${record.year_number}`) : 'Year unknown';
  return (
    <div className="bnf-com-drawer-grid" data-guide="record-facts">
      <FactRow
        label="Annual premium"
        value={record.premium_annual ?? ''}
        display={record.premium_annual != null ? formatMoney(record.premium_annual) : ''}
        readOnly={!isAll}
        placeholder="as billed"
        hint={record.premium_annual == null ? 'not known at booking — enter the final premium as billed' : origin('premium_annual')}
        onCommit={(raw) => onSave({ premium_annual: raw }, 'Premium updated')}
      />
      <div className="bb-account-row bnf-ov-row">
        <div className="bb-account-label">
          Carrier rate
          {origin('rate') && <div className="bb-drop-meta" style={{ fontWeight: 400 }}>{origin('rate')}</div>}
        </div>
        {isAll ? (
          <CompInput
            small
            value={record.rate}
            types={meta?.commission_types || []}
            onCommit={(comp) => onSave({ rate: comp || '' }, 'Rate updated')}
          />
        ) : (
          <div className="bb-account-value bnf-ov-readonly">{record.rate_label || '—'}</div>
        )}
      </div>
      <FactRow label="Carrier" value={record.carrier} readOnly={!isAll} placeholder="Carrier" onCommit={(raw) => onSave({ carrier: raw })} />
      <FactRow
        label="Policy number"
        value={record.policy_number}
        readOnly={!isAll}
        placeholder="from the carrier"
        onCommit={(raw) => onSave({ policy_number: raw })}
      />
      <FactRow
        label="Effective date"
        type="date"
        value={record.effective_date || ''}
        display={record.effective_date ? formatDate(record.effective_date) : ''}
        readOnly={!isAll}
        onCommit={(raw) => onSave({ effective_date: raw })}
      />
      <FactRow
        label="Term end"
        type="date"
        value={record.term_end || ''}
        display={record.term_end ? formatDate(record.term_end) : ''}
        readOnly={!isAll}
        onCommit={(raw) => onSave({ term_end: raw })}
      />
      <FactRow
        label="Enrolled (for PEPM)"
        value={record.employees ?? ''}
        readOnly={!isAll}
        placeholder="#"
        onCommit={(raw) => onSave({ employees: raw })}
      />
      <div className="bb-account-row bnf-ov-row">
        <div className="bb-account-label">Status</div>
        {isAll ? (
          <select
            className="bnf-intake-input"
            aria-label="Status"
            value={record.status}
            onChange={(event) => onSave({ status: event.target.value }, 'Status updated')}
          >
            {(meta?.commission?.statuses || []).map((status) => (
              <option key={status.key} value={status.key}>
                {status.label}
              </option>
            ))}
          </select>
        ) : (
          <div className="bb-account-value bnf-ov-readonly">{record.status_label}</div>
        )}
      </div>
      <FactRow label="Year" value={year} readOnly />
    </div>
  );
}
