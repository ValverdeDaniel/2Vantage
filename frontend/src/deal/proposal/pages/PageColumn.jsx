import cx from '../../../ui/cx';
import PlanLinkPicker from './PlanLinkPicker';

/*
 * One column's head on a page (plan.md §8.14; F37, F39, F43, F45, F52, J5, J10, J13, J50; the old ProposalPages.jsx
 * `head` at 7385bb3): its place, CURRENT k / RENEWAL / PRICED, "repeated", ‹ › and ✕, Today / Option n / the priced
 * label, the name (an option's or a renewal's opens the plan picker; a current plan's and a priced version's are plain
 * text), and "Replacing:". Every word and every allowance is the server's (proposals/page_columns.py); a plan shown
 * again keeps its tools where it first shows. Stop-loss columns are like any line's (OQ13).
 */

const CHIP = { current: 'bnf-chip-current', renewal: 'bnf-chip-renewal', priced: 'bnf-chip-concession' };

export default function PageColumn({ column, currents, busy, open, onPick, onMove, onRemove, onLink }) {
  const { plan, place, repeated } = column;
  const arrows = repeated ? null : plan.arrows;
  const remove = repeated ? null : plan.remove;
  const nameParts = (
    <>
      <span className="bnf-pg-carrier">{plan.carrier}</span>
      <span className={plan.pickable ? 'bnf-pg-plan' : undefined}>{plan.name}</span>
    </>
  );
  return (
    <th className={cx('bnf-pg-col', plan.kind === 'current' ? 'is-current' : 'is-option')} scope="col">
      <div className="bnf-pg-colhead">
        <span className="bnf-pg-place">{place}</span>
        {plan.chips.map((chip) => (
          <span key={chip.key} className={cx('bnf-plan-chip', CHIP[chip.key])} title={chip.title || undefined}>
            {chip.text}
          </span>
        ))}
        {repeated && (
          <span className="bnf-pg-repeat" title="Shown again on this page, as the slide shows it">
            repeated
          </span>
        )}
        <span className="bnf-pg-tools">
          {arrows && (
            <span className="bnf-pg-arrows">
              <button
                type="button"
                className="bnf-pg-arrow"
                disabled={busy || arrows.first}
                title="Show it earlier"
                aria-label={`Move ${plan.name} earlier`}
                onClick={() => onMove(plan, -1)}
              >
                ‹
              </button>
              <button
                type="button"
                className="bnf-pg-arrow"
                disabled={busy || arrows.last}
                title="Show it later"
                aria-label={`Move ${plan.name} later`}
                onClick={() => onMove(plan, 1)}
              >
                ›
              </button>
            </span>
          )}
          {remove && (
            <button
              type="button"
              className="bnf-pg-remove"
              disabled={busy || Boolean(remove.why)}
              title={remove.why || 'Take this plan off the proposal'}
              aria-label={`Take ${plan.name} off the proposal`}
              onClick={() => onRemove(plan)}
            >
              ✕
            </button>
          )}
        </span>
      </div>
      <div className="bnf-pg-title">{plan.title}</div>
      {plan.pickable ? (
        <button
          type="button"
          className={cx('bnf-pg-name', open && 'is-open')}
          disabled={busy}
          title="Change this plan: search every scanned quote"
          aria-haspopup="dialog"
          onClick={(event) => onPick(plan, event.currentTarget)}
        >
          {nameParts}
          <span className="bnf-pg-caret" aria-hidden="true">
            ▾
          </span>
        </button>
      ) : (
        <div className="bnf-pg-name is-plain">{nameParts}</div>
      )}
      <div className="bnf-pg-replacing">
        {plan.kind === 'current' ? (
          <span className="bnf-pg-today">{plan.replacing.text}</span>
        ) : plan.replacing.editable ? (
          <PlanLinkPicker plan={plan} currents={currents} disabled={busy} onChange={onLink} />
        ) : plan.replacing.text ? (
          <span className="bnf-link-picker-text">{plan.replacing.text}</span>
        ) : null}
      </div>
    </th>
  );
}
