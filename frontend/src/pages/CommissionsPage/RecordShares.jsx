import { useState } from 'react';
import { useParties, useSetShares } from '../../api/commission';
import { errorText } from '../../lib/errors';
import { formatMoney } from '../../lib/format';
import { useToast } from '../../ui/useToast';

/*
 * A record's shares (H55; 891f1b3 `commissions/RecordDrawer.jsx`'s splits column, its words and classes): each share
 * of agency revenue with its dollars, then the expected total. The all tier edits them: % per person, add a person by
 * role, remove one, and a reason that goes in the history; the server checks they total 100 % and names any error.
 * Typed shares override only this record, and "Put back the booked shares" drops them (H36 then freezes them anew).
 */
const ADD_ROLES = [
  ['secondary', 'Secondary'],
  ['split', 'Split'],
  ['referral', 'Referral'],
];

export default function RecordShares({ record, isAll }) {
  const toast = useToast();
  const save = useSetShares();
  const parties = useParties(false);
  const [draft, setDraft] = useState(null);
  const [reason, setReason] = useState('');
  const [role, setRole] = useState('split');
  const [errors, setErrors] = useState({});
  const people = [...(parties.data?.producers || []), ...(parties.data?.partners || [])].filter((p) => p.id);

  function start() {
    setDraft(record.shares.map((share) => ({ party: share.party, role: share.role, name: share.name, pct: share.pct })));
    setErrors({});
  }

  function send(shares, why, done) {
    save.mutate(
      { id: record.id, shares, reason: why },
      {
        onSuccess: () => {
          toast.success(done);
          setDraft(null);
          setReason('');
        },
        onError: (error) => {
          setErrors(error?.response?.data || {});
          toast.error(errorText(error));
        },
      },
    );
  }

  const add = (partyId) => {
    const person = people.find((entry) => entry.id === Number(partyId));
    if (!person || draft.some((row) => row.party === person.id)) return;
    setDraft([...draft, { party: person.id, role, name: person.name, pct: '0' }]);
  };

  if (!draft) {
    return (
      <div data-guide="record-splits">
        <div className="bnf-com-section-title">Splits (share of agency revenue)</div>
        {record.shares.map((share) => (
          <div key={`${share.role}-${share.party ?? 'house'}`} className="bnf-com-booked-line">
            <span>
              <span className={`bnf-com-kind bnf-com-kind-${share.kind}`}>{share.role_label}</span>{' '}
              {share.role === 'house' ? '' : share.name}
            </span>
            <span>
              {share.pct_label}
              {share.amount != null ? ` · ${formatMoney(share.amount)}` : ''}
            </span>
          </div>
        ))}
        <div className="bnf-com-booked-line" style={{ fontWeight: 600 }}>
          <span>Expected annual</span>
          <span className={record.expected != null ? 'bb-green' : 'bb-empty'}>
            {record.expected != null ? formatMoney(record.expected) : '— premium not known'}
          </span>
        </div>
        {record.typed_shares && record.reason && <div className="bb-drop-meta">Changed by hand: “{record.reason}”</div>}
        {isAll && (
          <div className="bnf-com-actions">
            <button type="button" className="btn btn-secondary btn-sm" onClick={start}>
              Edit splits
            </button>
            {record.typed_shares && (
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                disabled={save.isPending}
                onClick={() => send(null, '', 'The booked shares are back')}
              >
                Put back the booked shares
              </button>
            )}
          </div>
        )}
      </div>
    );
  }

  const fieldError = (key) => errors[key] && <div className="bnf-com-row-err">{errors[key]}</div>;
  return (
    <div className="bnf-com-splits-edit" data-guide="record-splits">
      <div className="bnf-com-section-title">Splits (share of agency revenue)</div>
      {draft.map((row, i) => (
        <div key={`${row.role}-${row.party ?? 'house'}`}>
          <div className="bnf-com-booked-line">
            <span>
              <span className="bnf-com-kind">{row.role}</span> {row.role === 'house' ? '' : row.name}
            </span>
            <span>
              <input
                aria-label={`Share for ${row.name}`}
                value={row.pct}
                onChange={(event) => setDraft(draft.map((x, j) => (j === i ? { ...x, pct: event.target.value } : x)))}
              />{' '}
              %
              {row.role !== 'house' && (
                <button
                  type="button"
                  className="bb-drop-remove"
                  style={{ marginLeft: 6 }}
                  title="Remove"
                  onClick={() => setDraft(draft.filter((_, j) => j !== i))}
                >
                  ×
                </button>
              )}
            </span>
          </div>
          {fieldError(`shares.${i}.pct`)}
          {fieldError(`shares.${i}.party`)}
        </div>
      ))}
      <div className="bnf-com-row">
        <select
          className="bnf-com-roleselect"
          aria-label="Role for the person you add next"
          value={role}
          onChange={(event) => setRole(event.target.value)}
        >
          {ADD_ROLES.map(([key, label]) => (
            <option key={key} value={key}>
              {label}
            </option>
          ))}
        </select>
        <select
          className="bnf-intake-input"
          aria-label="Add a person"
          value=""
          onChange={(event) => add(event.target.value)}
        >
          <option value="">＋ Add a person…</option>
          {people
            .filter((person) => !draft.some((row) => row.party === person.id))
            .map((person) => (
              <option key={person.id} value={person.id}>
                {person.name}
              </option>
            ))}
        </select>
      </div>
      {fieldError('shares.total')}
      <div className="bnf-com-row">
        <input
          className="bnf-intake-input"
          style={{ flex: 1 }}
          aria-label="Why the shares change"
          value={reason}
          placeholder="Why are the frozen splits changing? (required — goes in the history)"
          onChange={(event) => setReason(event.target.value)}
        />
      </div>
      {fieldError('reason')}
      <div className="bnf-com-actions">
        <button type="button" className="btn btn-secondary btn-sm" disabled={save.isPending} onClick={() => setDraft(null)}>
          Cancel
        </button>
        <button
          type="button"
          className="btn btn-primary btn-sm"
          disabled={save.isPending}
          onClick={() => send(draft.map(({ party, role: r, pct }) => ({ party, role: r, pct })), reason, 'Splits updated')}
        >
          Save splits
        </button>
      </div>
    </div>
  );
}
