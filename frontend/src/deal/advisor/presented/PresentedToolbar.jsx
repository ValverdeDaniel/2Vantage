import { AddQuotesButton, AddSbcsButton, TableLock } from '../../claude';

const LEGEND = [
  ['verified', 'Verified'],
  ['low', 'Review'],
  ['approved', 'Approved'],
  ['ignored', 'Ignored'],
  ['check', 'Needs checking'],
  ['missing', 'Missing'],
];

/*
 * The Proposal tab's toolbar over the board (plan.md §8.15; J71–J81; the old ComparisonGrid's `bnf-grid-toolbar` at
 * 891f1b3): the legend of the cells' review colours (J71); then the plan table's Claude lock (J72), ✎ Edit or ↶ Undo
 * and Done ✓ (J73, J74), ↺ Reset sizes with sizes of your own (J75), ★ Shortlist (n) / Show all N plans (J76),
 * ⤒ Import from template with ⬇ Template (J77), ＋ Add plan, greyed until ✎ Edit (J78), ＋ Add quotes and ＋ Add
 * SBCs, Work with Claude's doors (J79), ⟲ Re-read quotes (J80; with Claude set up: the deal's quote files read again,
 * waiting for review) and 🧭 Advisor (J81).
 */
export default function PresentedToolbar({ dealId, edit, sizes, shortlist, open, reread }) {
  return (
    <div className="bb-sov-toolbar bnf-grid-toolbar">
      <div className="bb-legend">
        {LEGEND.map(([key, label]) => (
          <span key={key} className="bb-legend-item">
            <span className={`bb-swatch bb-swatch-${key}`} />
            {label}
          </span>
        ))}
      </div>
      <div className="bb-toolbar-actions">
        <TableLock dealId={dealId} />
        {!edit.editing ? (
          <button type="button" className="btn btn-secondary btn-sm" title="Change values on this comparison" onClick={edit.enter}>
            ✎ Edit
          </button>
        ) : (
          <>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              disabled={!edit.canUndo}
              title="Put back the last value you changed this edit session (Ctrl+Z on the table does the same)"
              onClick={edit.undo}
            >
              ↶ Undo
            </button>
            <button type="button" className="btn btn-primary btn-sm" disabled={edit.leaving} onClick={edit.done}>
              {edit.leaving ? 'Saving…' : 'Done ✓'}
            </button>
          </>
        )}
        {sizes.custom && (
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            title="Plan columns back to five across and every row back to three lines (your sizes, in this browser)"
            onClick={sizes.reset}
          >
            ↺ Reset sizes
          </button>
        )}
        {shortlist.words && (
          <button
            type="button"
            className={`btn btn-sm ${shortlist.active ? 'btn-primary' : 'btn-secondary'}`}
            onClick={shortlist.toggle}
          >
            {shortlist.words}
          </button>
        )}
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
          onClick={open.downloadTemplate}
        >
          ⬇ Template
        </button>
        <span className="bnf-locked-hint" title={edit.editing ? '' : 'Click Edit to add a plan.'}>
          <button type="button" className="btn btn-secondary btn-sm" disabled={!edit.editing} onClick={open.addPlan}>
            ＋ Add plan
          </button>
        </span>
        <AddQuotesButton />
        <AddSbcsButton />
        {reread.available && (
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            disabled={reread.busy || edit.editing}
            title={edit.editing ? 'Press Done first' : 'Claude reads the quote files again; the read waits for your review'}
            onClick={reread.run}
          >
            {reread.busy ? 'Reading…' : '⟲ Re-read quotes'}
          </button>
        )}
        <button type="button" className="btn btn-secondary btn-sm" onClick={open.advisor}>
          🧭 Advisor
        </button>
      </div>
    </div>
  );
}
