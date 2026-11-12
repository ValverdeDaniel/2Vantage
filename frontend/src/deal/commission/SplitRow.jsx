import CompInput from '../shared/CompInput';
import PartySelect from '../../ui/PartySelect';
import { termsSet } from './splitModel';

/*
 * One secondary, split or referral row of the split editor (H12, H13, H15, H17, H121), in the old SplitsPanel's look
 * (891f1b3, `bnf-com-linerow`): the role, the person, the amount (a Comp), the share the preview gives it, the terms
 * toggle, "works it" (not on a referral) and ×. The terms: on renewal the same or a different amount (0 = first year
 * only), expires after N years, and the basis (of the producer pool, or of gross revenue). The year ladder is deferred
 * (H16). `share` is the server's {pct_label, amount_label}; the browser works nothing out.
 */
export default function SplitRow({ row, people, meta, used, share, error, disabled, onRole, onPick, onChange, onRemove }) {
  const vocab = meta.commission;
  const types = meta.commission_types || [];
  const marked = termsSet(row);
  return (
    <div className="bnf-com-linerow">
      <div className="bnf-com-row">
        <div className="bnf-com-row-label">
          <select
            className={`bnf-com-roleselect bnf-com-role-${row.role}`}
            value={row.role}
            title={vocab.role_hint}
            aria-label="Role"
            disabled={disabled}
            onChange={(event) => onRole(event.target.value)}
          >
            {vocab.other_roles.map((key) => (
              <option key={key} value={key}>
                {vocab.roles.find((entry) => entry.key === key)?.label || key}
              </option>
            ))}
          </select>
        </div>
        <PartySelect
          people={people}
          kinds={vocab.role_kinds[row.role]}
          groups={vocab.kind_groups}
          value={row.key}
          excludeKeys={used}
          disabled={disabled}
          onChange={onPick}
        />
        <CompInput small types={types} value={row.amount} disabled={disabled} label="Split amount"
          onCommit={(amount) => onChange({ amount })} />
        {share && (
          <span className="bnf-com-share">
            {share.pct_label}
            {share.amount_label ? ` · ${share.amount_label}` : ''}
          </span>
        )}
        <button
          type="button"
          className={`bnf-com-terms-toggle ${row.terms_open ? 'active' : ''}`}
          title="Renewal amount · expiry · basis"
          onClick={() => onChange({ terms_open: !row.terms_open }, { quiet: true })}
        >
          terms{marked ? ' •' : ''}
        </button>
        {row.role !== 'referral' && (
          <label className="bnf-com-active" title="Actively works the account">
            <input type="checkbox" checked={row.works_it} disabled={disabled}
              onChange={(event) => onChange({ works_it: event.target.checked })} />
            works it
          </label>
        )}
        {!disabled && (
          <button type="button" className="bb-drop-remove" title="Remove" aria-label="Remove this row" onClick={onRemove}>
            ×
          </button>
        )}
      </div>
      {row.terms_open && <Terms row={row} vocab={vocab} types={types} disabled={disabled} onChange={onChange} />}
      {error && <div className="bnf-com-row-err">{error}</div>}
    </div>
  );
}

function Terms({ row, vocab, types, disabled, onChange }) {
  const mode = row.renewal_amount ? 'different' : 'same';
  return (
    <div className="bnf-com-terms">
      <label>
        On renewal
        <select
          className="bnf-intake-input"
          value={mode}
          disabled={disabled}
          onChange={(event) =>
            onChange({
              renewal_amount: event.target.value === 'different' ? row.amount || { type: 'pct', value: '' } : null,
            })
          }
        >
          {vocab.renewal_modes.map((entry) => (
            <option key={entry.key} value={entry.key}>
              {entry.label}
            </option>
          ))}
        </select>
      </label>
      {row.renewal_amount && (
        <CompInput small types={types} value={row.renewal_amount} disabled={disabled} label="Renewal amount"
          onCommit={(amount) => onChange({ renewal_amount: amount || { type: 'pct', value: '0' } })} />
      )}
      <label>
        Expires after
        <input
          className="bnf-intake-input bnf-w-narrow"
          inputMode="numeric"
          placeholder="∞"
          aria-label="Expires after (years)"
          value={row.expires_after_years}
          disabled={disabled}
          style={{ width: 52 }}
          onChange={(event) => onChange({ expires_after_years: event.target.value.replace(/[^0-9]/g, '') })}
        />{' '}
        yrs
      </label>
      <label title={vocab.basis_hint}>
        Basis
        <select className="bnf-intake-input" value={row.basis} disabled={disabled}
          onChange={(event) => onChange({ basis: event.target.value })}>
          {vocab.bases.map((entry) => (
            <option key={entry.key} value={entry.key}>
              {entry.label}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}
