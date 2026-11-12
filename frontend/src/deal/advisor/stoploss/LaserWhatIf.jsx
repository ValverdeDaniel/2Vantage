import { Fragment } from 'react';
import { money, planWords } from './stopLossModel';

/*
 * ④ Laser detail and the what-if (plan.md §8.14; F104; the old StopLossAnalysis.jsx at 891f1b3): each column's
 * lasers named by position, never by claimant (rule 10), with what each adds above the specific deductible. Unticking
 * one asks the server for the analysis without it: the figures above move, nothing is saved, nothing reaches
 * Activity, and the exported workbook always prints every laser.
 */
export default function LaserWhatIf({ columns, dropped, onToggle }) {
  return (
    <div className="bb-grid-card">
      <div className="bnf-sl-section-title">Laser detail</div>
      <div className="bnf-sl-laser-note">
        Lasers by position, never a claimant. Untick a laser to model the carrier dropping it — the figures above move,
        nothing is saved, and the exported workbook always prints every laser.
      </div>
      <div className="bb-grid-scroll">
        <table className="bnf-sl-table bnf-sl-lasers">
          <thead>
            <tr>
              <th className="bnf-benefit-col">Laser</th>
              <th>Laser amount</th>
              <th>Specific deductible</th>
              <th>Additional liability</th>
              <th>Include</th>
            </tr>
          </thead>
          <tbody>
            {columns.map((column) => {
              const { lasers, spec_deductible: spec } = column.figures;
              const off = new Set(dropped[column.id] ?? []);
              return (
                <Fragment key={column.id}>
                  <tr className="bnf-group-row">
                    <td colSpan={5}>
                      {column.current ? 'CURRENT — ' : ''}
                      {planWords(column)}
                    </td>
                  </tr>
                  {lasers.length === 0 && (
                    <tr>
                      <td className="bnf-benefit-col bb-empty" colSpan={5}>
                        No lasers recorded on this option.
                      </td>
                    </tr>
                  )}
                  {lasers.map((laser) => (
                    <tr key={laser.n} className={off.has(laser.n) ? 'bnf-sl-laser-off' : ''}>
                      <td className="bnf-benefit-col">Laser {laser.n}</td>
                      <td className="bb-mono">{money(laser.amount)}</td>
                      <td className="bb-mono">{money(spec)}</td>
                      <td className="bb-mono">{money(laser.extra)}</td>
                      <td>
                        <input
                          type="checkbox"
                          checked={!off.has(laser.n)}
                          disabled={spec == null}
                          aria-label={`Include laser ${laser.n} of ${planWords(column)}`}
                          title={
                            spec == null
                              ? 'Enter the specific deductible before modelling this laser'
                              : 'Include this laser in the maximum annual liability'
                          }
                          onChange={() => onToggle(column.id, laser.n)}
                        />
                      </td>
                    </tr>
                  ))}
                  {lasers.length > 0 && (
                    <tr>
                      <td className="bnf-benefit-col">
                        <b>Total</b>
                      </td>
                      <td />
                      <td />
                      <td className="bb-mono">
                        <b>{money(column.figures.laser_liability)}</b>
                      </td>
                      <td />
                    </tr>
                  )}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
