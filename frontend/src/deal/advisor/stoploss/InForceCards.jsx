import { Fragment } from 'react';
import { cents, money, planWords, termText } from './stopLossModel';

/*
 * ① The contract in force (plan.md §8.14; F99; the old StopLossAnalysis.jsx snapshot at 891f1b3): one card row and
 * one terms line per current contract, each figure the server's.
 */
function SlCard({ label, value, note, verdict }) {
  return (
    <div className={`bnf-sl-card ${verdict ? 'bnf-sl-card-verdict' : ''}`}>
      <div className="bnf-sl-card-label">{label}</div>
      <div className="bnf-sl-card-value">{value}</div>
      {note && <div className="bnf-sl-card-note">{note}</div>}
    </div>
  );
}

export default function InForceCards({ currents, fields, terms }) {
  if (!currents.length) return null;
  return (
    <div>
      {currents.map((column) => {
        const f = column.figures;
        return (
          <Fragment key={column.id}>
            <div className="bnf-sl-section-title">
              In force — {column.carrier || 'carrier not recorded'}
              {column.name ? ` · ${column.name}` : ''}
            </div>
            <div className="bnf-sl-cards">
              <SlCard label="Specific deductible" value={money(f.spec_deductible)} note="per person" />
              <SlCard label="SL premium" value={cents(f.premium_pepm)} note={`${money(f.annual_premium)} / yr`} />
              <SlCard label="Admin / TPA" value={cents(f.admin_pepm)} note={`${money(f.annual_admin)} / yr`} />
              <SlCard
                label="Aggregate attachment"
                value={money(f.annual_attachment)}
                note={f.attachment_floor ? `floor ${money(f.attachment_floor)}` : 'floats with the census'}
              />
              <SlCard
                label="Laser liability"
                value={money(f.laser_liability)}
                note={f.laser_count == null ? 'spec deductible unknown' : `${f.laser_count} above spec`}
              />
              <SlCard
                label="Maximum annual liability"
                value={money(f.max_annual_liability)}
                note="premium + admin + attachment + lasers"
                verdict
              />
            </div>
            <div className="bnf-sl-terms" aria-label={`Contract terms of ${planWords(column)}`}>
              {terms.map((term) => (
                <span key={term.key} className="bnf-sl-term">
                  {term.label} <b>{termText(fields, term.key, column)}</b>
                </span>
              ))}
            </div>
          </Fragment>
        );
      })}
    </div>
  );
}
