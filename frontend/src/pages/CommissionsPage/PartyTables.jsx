import { labelOf } from '../../api/meta';
import CompInput from '../../deal/shared/CompInput';
import Badge from '../../ui/Badge';

/*
 * The two roster tables of Producers & partners (H97, H98, H101; old `bnf-com-table` in `bb-transfers-card`). Inline
 * edits are the all tier's: appointed, NPN, the producer's year-1 and renewal shares (blank = the firm default), a
 * partner's default split, deactivate (×) and reactivate. The access badge is the login's commission tier (H101; set
 * in Django admin). The house's rest beside a share comes from the server.
 */
const TIER_TONE = { none: 'danger', own: 'neutral', all: 'success' };
const TIER_WORD = { none: 'None', own: 'Own', all: 'All' };

export function ProducersTable({ rows, isAll, busy, onEdit }) {
  return (
    <div className="bb-transfers-card" style={{ marginBottom: 18 }} data-guide="parties-producers">
      <table className="bnf-com-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Login</th>
            <th>Appointed</th>
            <th>NPN</th>
            {isAll && <th>Year-1 producer / house</th>}
            {isAll && <th>Renewal producer / house</th>}
            {isAll && <th>Access</th>}
            <th />
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.key} className={row.active ? '' : 'inactive'}>
              <td>
                {row.name}
                {!row.active && <span className="bb-drop-meta"> · inactive</span>}
              </td>
              <td>{row.login_name || <span className="bb-empty">—</span>}</td>
              <td>
                {isAll ? (
                  <input type="checkbox" checked={row.appointed} disabled={busy} aria-label={`${row.name} appointed`}
                    onChange={(event) => onEdit(row, { appointed: event.target.checked })} />
                ) : row.appointed ? (
                  'yes'
                ) : (
                  'no'
                )}
              </td>
              <td>
                {isAll ? (
                  <input key={`npn:${row.npn}`} className="bnf-intake-input" style={{ width: 110 }} defaultValue={row.npn}
                    placeholder="NPN" aria-label={`${row.name} NPN`}
                    onBlur={(event) => event.target.value !== row.npn && onEdit(row, { npn: event.target.value })} />
                ) : (
                  row.npn || '—'
                )}
              </td>
              {isAll && <td><ShareCell row={row} field="first_year_pct" busy={busy} onEdit={onEdit} /></td>}
              {isAll && <td><ShareCell row={row} field="renewal_pct" busy={busy} onEdit={onEdit} /></td>}
              {isAll && <td>{row.tier ? <Badge tone={TIER_TONE[row.tier]}>{TIER_WORD[row.tier]}</Badge> : null}</td>}
              <td><ActiveCell row={row} isAll={isAll} onEdit={onEdit} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function PartnersTable({ rows, isAll, busy, meta, onEdit }) {
  return (
    <div className="bb-transfers-card" data-guide="parties-partners">
      <table className="bnf-com-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Kind</th>
            <th>Default split</th>
            <th>Contact</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 && (
            <tr>
              <td colSpan={5} className="bnf-com-empty">
                No partners yet.
              </td>
            </tr>
          )}
          {rows.map((row) => (
            <tr key={row.key} className={row.active ? '' : 'inactive'}>
              <td>
                {row.name}
                {!row.active && <span className="bb-drop-meta"> · inactive</span>}
              </td>
              <td>
                <span className={`bnf-com-kind bnf-com-kind-${row.kind}`}>{labelOf(meta.commission.kinds, row.kind)}</span>
              </td>
              <td>
                {isAll ? (
                  <CompInput small types={meta.commission_types || []} value={row.default_split} disabled={busy}
                    label={`${row.name} default split`} onCommit={(comp) => onEdit(row, { default_split: comp || '' })} />
                ) : (
                  row.default_split_label || '—'
                )}
              </td>
              <td>{row.email || '—'}</td>
              <td><ActiveCell row={row} isAll={isAll} onEdit={onEdit} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ShareCell({ row, field, busy, onEdit }) {
  const value = row[field];
  const house = row[field.replace('_pct', '_house_pct')];
  return (
    <span className="bnf-com-inline-edit"
      title={value == null ? 'No share of their own — the firm default applies. Type a % to set one.' : undefined}>
      <input
        key={`${field}:${value}`}
        defaultValue={value ?? ''}
        placeholder="default"
        disabled={busy}
        aria-label={`${row.name} ${field === 'first_year_pct' ? 'year-1' : 'renewal'} producer share`}
        onBlur={(event) => {
          const raw = event.target.value.trim();
          if (raw !== (value ?? '')) onEdit(row, { [field]: raw });
        }}
        onKeyDown={(event) => event.key === 'Enter' && event.currentTarget.blur()}
      />
      <span className="bb-drop-meta">%{house != null ? ` / ${house}%` : ''}</span>
    </span>
  );
}

function ActiveCell({ row, isAll, onEdit }) {
  if (!isAll) return null;
  if (row.active) {
    return (
      <button type="button" className="bb-drop-remove" style={{ marginLeft: 8 }} title="Deactivate"
        aria-label={`Deactivate ${row.name}`} onClick={() => onEdit(row, { active: false }, 'Deactivated')}>
        ×
      </button>
    );
  }
  return (
    <button type="button" className="btn btn-secondary btn-sm" style={{ marginLeft: 8 }}
      onClick={() => onEdit(row, { active: true }, 'Reactivated')}>
      reactivate
    </button>
  );
}
