import { useAddCoverage, useEditCoverage, useRemoveCoverage } from '../../api/intake';
import { errorText } from '../../lib/errors';
import { useToast } from '../../ui/useToast';
import CompInput from '../shared/CompInput';

/*
 * Current coverage (B14; OQ15: kept beside the intent card, both editing the same rows through one service): one
 * subcard per row — line, carrier and ×; funding, renewal date and notes; the in-force commission and where it came
 * from — and "＋ Add coverage line". The old Intake tab's subcards (891f1b3 `IntakeTab.jsx`), same classes. Once the
 * line has current plans in the Advisor, carrier and funding show theirs, read-only (§6.5).
 */
const LABEL_WIDTH = { flex: '0 0 150px' }; // the old subcard's inline width for the commission label

function Subcard({ row, meta, busy, onSave, onRemove }) {
  const funding = meta?.funding || [];
  const fromPlans = row.from_plans;
  const sources = meta?.intake?.coverage?.commission_sources || [];
  const blur = (key, current) => (event) => event.target.value !== (current || '') && onSave({ [key]: event.target.value });
  return (
    <div className="bnf-subcard">
      <div className="bnf-subcard-row">
        <select
          className="bnf-intake-input bnf-w-narrow"
          value={row.line}
          aria-label="Line of coverage"
          disabled={busy}
          onChange={(event) => onSave({ line: event.target.value })}
        >
          {(meta?.lines || []).map((line) => (
            <option key={line.key} value={line.key}>
              {line.label}
            </option>
          ))}
        </select>
        {fromPlans ? (
          <input className="bnf-intake-input" value={fromPlans.carrier} readOnly aria-label="Carrier"
            title="From the current plans in the Advisor — edit them there" />
        ) : (
          <input
            key={`carrier:${row.carrier}`}
            className="bnf-intake-input"
            defaultValue={row.carrier}
            placeholder="Carrier"
            aria-label="Carrier"
            onBlur={blur('carrier', row.carrier)}
          />
        )}
        <button type="button" className="bb-drop-remove" title="Remove line" aria-label={`Remove ${row.label}`}
          disabled={busy} onClick={onRemove}>
          ×
        </button>
      </div>
      <div className="bnf-subcard-row">
        <select
          className="bnf-intake-input bnf-w-narrow"
          value={fromPlans ? fromPlans.funding : row.funding}
          aria-label="Funding"
          disabled={busy || Boolean(fromPlans)}
          title={fromPlans ? 'From the current plans in the Advisor — edit them there' : undefined}
          onChange={(event) => onSave({ funding: event.target.value })}
        >
          <option value="">Funding…</option>
          {funding.map((option) => (
            <option key={option.key} value={option.key}>
              {option.label}
            </option>
          ))}
        </select>
        <input
          key={`renewal:${row.renewal_date || ''}`}
          type="date"
          className="bnf-intake-input bnf-w-narrow"
          defaultValue={row.renewal_date || ''}
          title="Renewal date"
          aria-label="Renewal date"
          onBlur={blur('renewal_date', row.renewal_date)}
        />
        <input
          key={`notes:${row.notes}`}
          className="bnf-intake-input"
          defaultValue={row.notes}
          placeholder="Notes (plan design, rates…)"
          aria-label="Notes"
          maxLength={300}
          onBlur={blur('notes', row.notes)}
        />
      </div>
      <div className="bnf-subcard-row bnf-com-inforce">
        <span className="bb-drop-meta" style={LABEL_WIDTH} title="What the incumbent carrier pays today — needed for the AOR letter">
          In-force commission
        </span>
        <CompInput small value={row.commission} types={meta?.commission_types || []} disabled={busy}
          label="In-force commission" onCommit={(comp) => onSave({ commission: comp || '' })} />
        <select
          className="bnf-intake-input bnf-w-narrow"
          value={row.commission_source || ''}
          title="Where the in-force number came from"
          aria-label="Where the in-force commission came from"
          disabled={busy}
          onChange={(event) => onSave({ commission_source: event.target.value })}
        >
          <option value="">Source…</option>
          {sources.map((option) => (
            <option key={option.key} value={option.key}>
              {option.label}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}

// A new subcard starts on Medical, as the old one did, else on the first line.
const firstLine = (meta) => (meta?.lines || []).find((line) => line.key === 'medical')?.key || meta?.lines?.[0]?.key;

export default function CurrentCoverageCard({ deal, meta, coverage }) {
  const toast = useToast();
  const add = useAddCoverage(deal.id);
  const edit = useEditCoverage(deal.id);
  const remove = useRemoveCoverage(deal.id);
  const busy = add.isPending || edit.isPending || remove.isPending;
  const failed = (fallback) => ({ onError: (error) => toast.error(errorText(error, { fallback })) });
  return (
    <div className="bb-panel bnf-intake-section">
      <div className="bb-panel-title">Current coverage</div>
      <div className="bb-panel-sub">One row per incumbent line</div>
      {coverage.map((row) => (
        <Subcard
          key={row.id}
          row={row}
          meta={meta}
          busy={busy}
          onSave={(changes) => edit.mutate({ id: row.id, changes }, failed('Could not save the coverage line.'))}
          onRemove={() => remove.mutate(row.id, failed('Could not remove the coverage line.'))}
        />
      ))}
      <button
        type="button"
        className="btn btn-secondary btn-sm"
        disabled={busy}
        onClick={() => add.mutate({ line: firstLine(meta) }, failed('Could not add the coverage line.'))}
      >
        ＋ Add coverage line
      </button>
    </div>
  );
}
