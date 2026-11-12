import { useState } from 'react';

/*
 * What the reformat did to this census, said before anything is applied (C13, C15). Ported from old Vantage 891f1b3
 * `CensusReformatBanner.jsx`: a one-row-per-benefit file is combined into one row per person, the lines found and the
 * things worth checking are shown, and "Use the original file instead" is one click away (here a PATCH with
 * {reformat: false} on the import). A file in the grey band, or one the reformat refused, needs attention.
 */
export default function ReformatBanner({ imp, onUseOriginal, busy }) {
  const [showDetail, setShowDetail] = useState(false);
  const pivot = imp.pivot || {};
  const reason = pivot.applied ? '' : pivot.reason || '';
  if (!pivot.applied && !reason) return null;

  if (reason) {
    return (
      <div className="bnf-reformat-banner bnf-reformat-attention">
        <div className="bnf-reformat-title">
          There&apos;s an issue with this client census — unable to reformat, needs attention.
        </div>
        <div className="bnf-reformat-body">{reason}</div>
        <div className="bnf-reformat-body">
          Map the columns manually below, or ask the client for a census with one row per employee.
        </div>
      </div>
    );
  }

  const lines = (pivot.lines || []).join(', ');
  const conflicts = pivot.conflicts || [];
  return (
    <div className="bnf-reformat-banner bnf-reformat-done">
      <div className="bnf-reformat-title">Reformatted this census</div>
      <div className="bnf-reformat-body">
        This file listed each person once per benefit. We combined it into{' '}
        <strong>
          {pivot.source_rows} benefit rows → {pivot.employee_rows} employee
          {pivot.employee_rows === 1 ? '' : 's'} and {pivot.dependent_rows} dependent
          {pivot.dependent_rows === 1 ? '' : 's'}
        </strong>
        {lines ? <> — lines found: {lines}.</> : '.'}
      </div>
      {conflicts.length > 0 && (
        <div className="bnf-reformat-body">
          <button type="button" className="bnf-reformat-link" onClick={() => setShowDetail((shown) => !shown)}>
            {showDetail ? 'Hide' : 'Show'} {conflicts.length} thing
            {conflicts.length === 1 ? '' : 's'} worth checking
          </button>
          {showDetail && (
            <ul className="bnf-reformat-list">
              {conflicts.map((note) => (
                <li key={note}>{note}</li>
              ))}
            </ul>
          )}
        </div>
      )}
      <button type="button" className="btn btn-secondary btn-sm" onClick={onUseOriginal} disabled={busy}>
        {busy ? 'Restoring…' : 'Use the original file instead'}
      </button>
    </div>
  );
}
