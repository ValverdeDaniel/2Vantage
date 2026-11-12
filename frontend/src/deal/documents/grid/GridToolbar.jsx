import cx from '../../../ui/cx';
import { HotkeyLegend, ReviewDone } from '../../../valuereview/HotkeyLegend';
import PickBar from '../../../valuereview/PickBar';

/*
 * The row above the station's Grid (plan.md §8.16; E50, E52, E54, E55, D123, D125; the old GridReviewToolbar): which
 * plans and rows to show, what the picked cells are and what to do with them, and the keys — always on screen, in
 * their own line, with the last action and its ↶ Undo. In ✎ Edit the pick and the review keys give way to the edit
 * keys (E67), with the session's ↶ Undo (Ctrl+Z on the grid does the same) and Done ✓. `filter` = {mode, plans,
 * errorPlans, rowsOnly, onMode, onRowsOnly}; `pick` as PickBar's, or null; `edit` = {canUndo, undo, done, leaving}.
 */
export default function GridToolbar({ filter, pick, done, onUndo, undoing, edit }) {
  return (
    <div className="gs-toolbar">
      {filter && (
        <div className="gs-filters" role="toolbar" aria-label="Which plans to show">
          <button
            type="button"
            className={cx('bnf-frl-chip', filter.mode === 'all' && 'is-on')}
            aria-pressed={filter.mode === 'all'}
            onClick={() => filter.onMode('all')}
          >
            All plans <b>{filter.plans}</b>
          </button>
          <button
            type="button"
            className={cx('bnf-frl-chip bnf-frl-tone-amber', filter.mode === 'errors' && 'is-on')}
            aria-pressed={filter.mode === 'errors'}
            disabled={!filter.errorPlans}
            onClick={() => filter.onMode('errors')}
            title="Only the plans with a value from this file the AI flagged, someone marked as needing checking, or code could not find in the file"
          >
            ⚠ Potential errors <b>{filter.errorPlans}</b>
          </button>
          <label className="gs-rows-only" title="Hide the benefits with no potential error in any plan shown">
            <input
              type="checkbox"
              checked={filter.rowsOnly}
              disabled={!filter.errorPlans}
              onChange={(event) => filter.onRowsOnly(event.target.checked)}
            />
            Only rows with potential errors
          </label>
        </div>
      )}
      {pick && <PickBar pick={pick} />}
      {pick && (
        <div className="gs-legend-row">
          <ReviewDone done={done} onUndo={onUndo} undoing={undoing} />
          <HotkeyLegend review={pick.review} />
        </div>
      )}
      {edit && (
        <div className="gs-legend-row">
          <HotkeyLegend edit />
          <button
            type="button"
            className="btn btn-sm btn-secondary"
            disabled={!edit.canUndo}
            title="Put back the last value you changed in the grid this edit session (Ctrl+Z on the grid does the same)"
            onClick={edit.undo}
          >
            ↶ Undo
          </button>
          <button type="button" className="btn btn-primary btn-sm" disabled={edit.leaving} onClick={edit.done}>
            {edit.leaving ? 'Saving…' : 'Done ✓'}
          </button>
        </div>
      )}
    </div>
  );
}
