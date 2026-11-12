import { Link } from 'react-router';
import { useSetRate } from '../../api/commission';
import { errorText } from '../../lib/errors';
import { formatMoney } from '../../lib/format';
import { useToast } from '../../ui/useToast';
import CompInput from '../shared/CompInput';

/*
 * Commission per line (H3–H8; 891f1b3 `overview/CommissionPanel.jsx`, its words and classes): line · in-force (the
 * incumbent's commission and carrier, the source on hover) · the agreed rate (CompInput; "agency default" or "not set")
 * · Expected / yr with its basis inline ("$X/yr premium · carrier — plan", the plans on hover). A line in force with a
 * commission that is not being quoted shows muted. Every figure comes from the server; a rate edit merges one line.
 */
export default function RatesGrid({ dealId, payload, meta }) {
  const toast = useToast();
  const setRate = useSetRate(dealId);
  const types = meta.commission_types || [];

  function commit(line) {
    return (comp) =>
      setRate.mutate(
        { [line]: comp || '' },
        { onError: (error) => toast.error(`Commission: ${errorText(error)}`) },
      );
  }

  return (
    <div className="bb-panel bnf-ov-commission" data-guide="overview-commission">
      <div className="bb-panel-title">Commission per line</div>
      <div className="bb-panel-sub">
        What the incumbent pays today (from the Intake coverage lines) · what we agreed with the carrier · what it is
        worth. <Link to={`/deals/${dealId}/intake`}>Edit in-force on Intake ↗</Link>
      </div>

      <div className="bnf-com-grid" data-guide="commission-grid">
        <div className="bnf-com-grid-head">
          <span>Line</span>
          <span>In-force</span>
          <span>Agreed rate</span>
          <span className="bnf-com-num">Expected / yr</span>
        </div>
        {payload.rows.map((row) => (
          <div key={row.line} className={`bnf-com-grid-row ${row.not_requested ? 'bnf-com-grid-muted' : ''}`}>
            <span className="bnf-com-grid-line">
              {row.label}
              {row.not_requested ? <span className="bb-drop-meta"> · not being quoted</span> : null}
            </span>
            <InForce found={row.in_force} />
            <span className="bnf-com-grid-req">
              {row.not_requested ? (
                <span className="bb-empty">—</span>
              ) : (
                <>
                  <CompInput small types={types} value={row.rate} label={`${row.label} agreed rate`}
                    disabled={setRate.isPending} onCommit={commit(row.line)} />
                  {row.source === 'agency' && (
                    <span className="bb-drop-meta"> {row.effective_label} ({row.source_label})</span>
                  )}
                  {row.source === '' && <span className="bb-drop-meta"> {row.source_label}</span>}
                </>
              )}
            </span>
            <Expected row={row} />
          </div>
        ))}
      </div>

      <div className="bnf-ov-comm-total">
        <span>Expected annual revenue</span>
        <span className="bb-mono bnf-ov-comm-totalvalue">{payload.total != null ? formatMoney(payload.total) : '—'}</span>
      </div>
      <div className="bb-drop-meta bnf-ov-comm-note">{payload.note}</div>
    </div>
  );
}

function InForce({ found }) {
  const title = found?.carrier ? [found.carrier, found.source_label].filter(Boolean).join(' · ') : '';
  return (
    <span className="bnf-com-grid-inforce" title={title}>
      {found?.label ? (
        <>
          {found.label}
          {found.carrier ? <span className="bb-drop-meta"> {found.carrier}</span> : null}
        </>
      ) : found ? (
        <>
          <span className="bb-empty">set on Intake</span>
          {found.carrier ? <span className="bb-drop-meta"> {found.carrier}</span> : null}
        </>
      ) : (
        <span className="bb-empty">no incumbent</span>
      )}
    </span>
  );
}

function Expected({ row }) {
  const basis = row.basis;
  const title = basis ? [...basis.plans, basis.enrollment_source].filter(Boolean).join('\n') : '';
  let words = '';
  if (basis?.annual != null) words = `${formatMoney(basis.annual)}/yr premium · ${basis.label}`;
  else if (basis?.reason) words = basis.reason;
  else if (!row.not_requested) words = 'premium not known yet';
  return (
    <span className={`bnf-com-num bb-mono ${row.expected != null ? 'bb-green' : 'bb-empty'}`}>
      {row.expected != null ? formatMoney(row.expected) : '—'}
      <div className="bb-drop-meta bnf-com-grid-basis" title={title}>
        {words}
      </div>
    </span>
  );
}
