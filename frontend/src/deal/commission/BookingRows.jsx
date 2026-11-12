import { useEditRecord } from '../../api/commission';
import { errorText } from '../../lib/errors';
import { formatMoney } from '../../lib/format';
import { useToast } from '../../ui/useToast';
import CompInput from '../shared/CompInput';

/*
 * The booking summary's table (H35, H37; 891f1b3 `BookingSummaryModal.jsx`): line · carrier · rate · premium ·
 * expected · house · holes, a row with holes tinted. The all tier fills a hole right here: the rate (CompInput), the
 * premium as billed and the enrolled count for a PEPM rate, each a typed fact (H54). Every figure is the server's.
 */
export default function BookingRows({ records, canEdit, meta }) {
  const toast = useToast();
  const edit = useEditRecord();
  const holeWords = meta.commission?.holes || {};
  const types = meta.commission_types || [];
  const busy = edit.isPending;

  function save(record, changes, done) {
    edit.mutate(
      { id: record.id, changes },
      { onSuccess: () => toast.success(done), onError: (error) => toast.error(errorText(error)) },
    );
  }

  return (
    <table className="bnf-com-table bnf-com-booking-table" data-guide="booking-table">
      <thead>
        <tr>
          <th>Line</th>
          <th>Carrier</th>
          <th>Rate</th>
          <th className="bnf-com-num">Premium / yr</th>
          <th className="bnf-com-num">Expected</th>
          {canEdit && <th className="bnf-com-num">House</th>}
          <th>Holes</th>
        </tr>
      </thead>
      <tbody>
        {records.map((record) => {
          const holes = record.holes || [];
          return (
            <tr key={record.id} className={holes.length ? 'bnf-com-hasholes' : ''}>
              <td>
                {record.line_label}
                {record.plan_label ? <div className="bb-drop-meta">{record.plan_label}</div> : null}
              </td>
              <td>{record.carrier || '—'}</td>
              <td>
                {canEdit && holes.includes('rate') ? (
                  <CompInput
                    small
                    value={record.rate}
                    types={types}
                    disabled={busy}
                    onCommit={(comp) => save(record, { rate: comp || '' }, 'Rate set')}
                  />
                ) : (
                  record.rate_label || <span className="bnf-com-hole">not set</span>
                )}
              </td>
              <td className="bnf-com-num">
                {canEdit && holes.includes('premium') ? (
                  <input
                    className="bnf-intake-input"
                    style={{ width: 110, textAlign: 'right' }}
                    placeholder="as billed"
                    aria-label={`Premium as billed for ${record.line_label}`}
                    disabled={busy}
                    onKeyDown={(event) => event.key === 'Enter' && event.currentTarget.blur()}
                    onBlur={(event) =>
                      event.target.value.trim() &&
                      save(record, { premium_annual: event.target.value }, 'Premium set')
                    }
                  />
                ) : record.premium_annual != null ? (
                  formatMoney(record.premium_annual)
                ) : (
                  <span className="bnf-com-hole">not known</span>
                )}
              </td>
              <td className={`bnf-com-num ${record.expected != null ? 'bb-green' : 'bnf-com-hole'}`}>
                {record.expected != null ? formatMoney(record.expected) : '—'}
              </td>
              {canEdit && (
                <td className="bnf-com-num">{record.house_share != null ? formatMoney(record.house_share) : '—'}</td>
              )}
              <td>
                {holes.map((hole) => (
                  <span key={hole} className="bb-badge bb-badge-amber" style={{ marginRight: 4 }}>
                    {holeWords[hole]?.short || hole}
                  </span>
                ))}
                {canEdit && holes.includes('employees') && (
                  <input
                    className="bnf-intake-input"
                    style={{ width: 60 }}
                    placeholder="#"
                    aria-label={`Enrolled for ${record.line_label}`}
                    disabled={busy}
                    onBlur={(event) =>
                      event.target.value.trim() && save(record, { employees: event.target.value }, 'Enrolled set')
                    }
                  />
                )}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
