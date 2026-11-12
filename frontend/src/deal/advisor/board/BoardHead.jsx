import { useNavigate } from 'react-router';
import LineTabs from '../LineTabs';

/*
 * The board header (plan.md §8.14; F5, F9–F11, F68, F73, F93–F96; the old `bnf-advisor-boardhead`): this line's tabs
 * and count on the left, its actions on the right. Outside ✎ Edit: ⤓ Export, the summary tiers card, ⤒ Import from
 * template with ⬇ Template, ✎ Edit. In Edit (a screen mode only, F68): ＋ Add plan, Clear all plans, where a priced
 * version's editor sits (⌸, slice 35), ↶ Undo and Done ✓, and the banner whose "change history ▸" opens Activity. With stars: View shortlist in proposal ▸ and
 * Clear shortlist (this line only, F55).
 */
export default function BoardHead({ dealId, lines, line, onLine, count, editing, starred, ui }) {
  const navigate = useNavigate();
  const { open, edit, actions, busy } = ui;
  return (
    <div className="bnf-advisor-boardhead">
      <LineTabs lines={lines} line={line} onPick={onLine} />
      <div className="bnf-advisor-boardhead-row">
        <div className="bnf-advisor-boardhead-main">
          <div className="bnf-filter-count">{count}</div>
          {editing && (
            <span className="bnf-conc-editing-note">
              editing — work the table like a spreadsheet: click a cell and type, Tab →, Enter ↓. A typed number sits
              over the carrier’s, which stays in the{' '}
              <button type="button" className="bnf-pv-doclink" onClick={open.activity}>
                change history ▸
              </button>
              .
            </span>
          )}
        </div>
        <span className="bnf-count-actions">
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            disabled={busy.exporting}
            title="Download these plans and these columns as a spreadsheet — the board as it stands"
            onClick={actions.exportBoard}
          >
            {busy.exporting ? 'Building…' : '⤓ Export'}
          </button>
          {ui.counts && (
            <button
              type="button"
              className="btn btn-sm btn-secondary"
              title="Type how many employees each plan covers by tier (EE, ES, EC, FAM). Those counts price the plans you pick."
              onClick={open.counts}
            >
              {ui.counts.typed ? `Summary tiers · On (${ui.counts.typed})` : `＋ Add summary ${ui.counts.label} tiers`}
            </button>
          )}
          {!editing ? (
            <>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                title="Bring in plans from a filled plan template: read in code, no AI, checked before anything changes"
                onClick={open.importing}
              >
                ⤒ Import from template
              </button>
              <button
                type="button"
                className="bnf-marketing-guide-link"
                title="A workbook with every benefit row for this line and a column per plan"
                onClick={actions.downloadTemplate}
              >
                ⬇ Template
              </button>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                title="Correct any number in the table — a typed number sits over the carrier's, and every change is in the change history"
                onClick={edit.enter}
              >
                ✎ Edit
              </button>
            </>
          ) : (
            <>
              <button type="button" className="btn btn-secondary btn-sm" onClick={open.addPlan}>
                ＋ Add plan
              </button>
              <button
                type="button"
                className="btn btn-danger btn-sm"
                disabled={busy.remove || !ui.quoteCount}
                title="Remove every quoted plan on this line and start over. Current and sold plans stay; Undo brings the rest back."
                onClick={open.clearLine}
              >
                Clear all plans
              </button>
              {edit.priced && (
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  title={
                    edit.priced.mode === 'row'
                      ? 'A priced version is edited in the table, under its plan. Switch to the box above the table — the draft rows stay either way.'
                      : 'A priced version is edited in the box above the table. Switch back to editing under the plan itself.'
                  }
                  onClick={edit.priced.toggleMode}
                >
                  {edit.priced.mode === 'row' ? '⌸ Editing in the table' : '⌸ Editing above the table'}
                </button>
              )}
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                disabled={!edit.canUndo}
                title="Put back the last value you changed in the table this edit session (Ctrl+Z on the table does the same)"
                onClick={edit.undo}
              >
                ↶ Undo
              </button>
              <button type="button" className="btn btn-primary btn-sm" disabled={edit.leaving} onClick={edit.done}>
                {edit.leaving ? 'Saving…' : 'Done ✓'}
              </button>
            </>
          )}
          {starred > 0 && (
            <>
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={() => navigate(`/deals/${dealId}/proposal`)}
              >
                View shortlist in proposal ▸
              </button>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                title="Remove every star on this line"
                onClick={actions.clearShortlist}
              >
                Clear shortlist
              </button>
            </>
          )}
        </span>
      </div>
    </div>
  );
}
