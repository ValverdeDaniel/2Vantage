import FromClientToggle from '../shared/FromClientToggle';

/*
 * The roster's toolbar (plan.md §8.10; C3, C4, C7, C8, C38; the old CensusGrid toolbar at 891f1b3): the legend of
 * cell colours on the left, the actions on the right. Outside ✎ Edit: ✎ Edit, ＋ Add employee (greyed until Edit),
 * ⟲ Re-map source file, ⬇ Blank template, ☑ Select cells, ＋ Ask ▸ (the request tray arrives with Review & requests)
 * and ⬇ Export (the census workbook, §9.2; carrier census files moved to the RFP, C31). In Edit (a client-side mode,
 * C4): "These came from the client", ＋ Add employee, Clear roster, ↶ Undo and Done ✓ (the Advisor's Edit, F68). While
 * picking cells: Select all missing and Cancel.
 */

function Legend() {
  // "On file", not "Verified" (D-124): a confident cell may be imported, typed or read by AI.
  const items = [
    ['bb-swatch-verified', 'On file'],
    ['bb-swatch-low', 'Review'],
    ['bb-swatch-client', 'From the client'],
    ['bb-swatch-approved', 'Approved'],
    ['bb-swatch-ignored', 'Ignored'],
    ['bb-swatch-check', 'Needs checking'],
    ['bb-swatch-missing', 'Missing'],
    ['bnf-swatch-error', 'Error'],
  ];
  return (
    <div className="bb-legend">
      {items.map(([swatch, label]) => (
        <span key={label} className="bb-legend-item">
          <span className={`bb-swatch ${swatch}`} />
          {label}
        </span>
      ))}
    </div>
  );
}

export default function RosterToolbar({ mode, edit, actions, busy }) {
  const { editing, picking } = mode;
  return (
    <div className="bb-sov-toolbar bnf-grid-toolbar">
      <Legend />
      <div className="bb-toolbar-actions">
        {picking ? (
          <>
            <button type="button" className="btn btn-secondary btn-sm" onClick={actions.selectMissing}>
              Select all missing
            </button>
            <button type="button" className="btn btn-secondary btn-sm" onClick={actions.stopPicking}>
              Cancel
            </button>
          </>
        ) : editing ? (
          <>
            <FromClientToggle checked={edit.relay} onChange={edit.setRelay} />
            <button type="button" className="btn btn-secondary btn-sm" onClick={actions.addEmployee}>
              ＋ Add employee
            </button>
            <button
              type="button"
              className="btn btn-danger btn-sm"
              title="Remove everyone on the roster. A later import brings people back by who they are."
              onClick={actions.askClear}
            >
              Clear roster
            </button>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              disabled={!edit.canUndo}
              title="Put back the last value you changed on the roster this edit session (Ctrl+Z on the grid does the same)"
              onClick={edit.undo}
            >
              ↶ Undo
            </button>
            <button type="button" className="btn btn-primary btn-sm" disabled={edit.leaving} onClick={edit.done}>
              {edit.leaving ? 'Saving…' : 'Done ✓'}
            </button>
          </>
        ) : (
          <>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              title="Change values on the roster"
              onClick={edit.enter}
            >
              ✎ Edit
            </button>
            <span className="bnf-locked-hint" title="Click Edit to add an employee.">
              <button type="button" className="btn btn-secondary btn-sm" disabled>
                ＋ Add employee
              </button>
            </span>
            {actions.remap && (
              <button type="button" className="btn btn-secondary btn-sm" disabled={busy.remap} onClick={actions.remap}>
                ⟲ Re-map source file
              </button>
            )}
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              title="Our blank census template — send it to the client to fill in"
              disabled={busy.template}
              onClick={actions.template}
            >
              ⬇ Blank template
            </button>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              title="Pick cells to approve, ignore, flag or ask the client about"
              onClick={actions.startPicking}
            >
              ☑ Select cells
            </button>
            <button
              type="button"
              className="btn btn-violet btn-sm"
              disabled
              title="Asking the client goes through the request tray, which arrives with Review & requests"
            >
              ＋ Ask ▸
            </button>
            <button
              type="button"
              className="btn btn-primary btn-sm"
              title="The whole census as a workbook, with each person's issues (staff only: SSNs unmasked)"
              disabled={busy.export}
              onClick={actions.exportCensus}
            >
              ⬇ Export
            </button>
          </>
        )}
      </div>
    </div>
  );
}
