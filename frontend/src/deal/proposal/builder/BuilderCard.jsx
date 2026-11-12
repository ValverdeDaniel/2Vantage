import cx from '../../../ui/cx';
import CompletedMark from './CompletedMark';

/*
 * One card on the proposal builder (plan.md §8.14; J18; the old BuilderCard.jsx at 891f1b3): every card collapses and
 * can be marked completed ("I reviewed this, it is what I want"). Marking it collapses it; a completed card starts
 * collapsed for everyone on the deal. The builder owns the open state and the marks; this only draws them. The toggle
 * is a real button, so a blur on a half-typed note in the body commits before the body unmounts.
 */
export default function BuilderCard({ title, chips = null, summary = '', card, guide, children }) {
  const { done, open, busy, onToggleOpen, onToggleDone } = card;
  const name = typeof title === 'string' ? title : 'this card';
  return (
    <div className={cx('bb-panel bnf-build-panel bnf-bcard', done && 'bnf-bcard-done', !open && 'bnf-bcard-shut')} data-guide={guide}>
      <div className="bnf-bcard-head">
        <button
          type="button"
          className="bnf-card-toggle bnf-bcard-toggle"
          aria-expanded={open}
          aria-label={open ? `Collapse ${name}` : `Expand ${name}`}
          title={open ? 'Collapse this card' : 'Expand this card'}
          onClick={onToggleOpen}
        >
          <span className={cx('bnf-req-chevron', open && 'expanded')} aria-hidden="true">
            ▶
          </span>
          <span className="bb-panel-title bnf-bcard-title">{title}</span>
        </button>
        {chips}
        {summary && <span className="bnf-bcard-summary">{summary}</span>}
        <CompletedMark done={done} busy={busy} onToggleDone={onToggleDone} />
      </div>
      {open && children}
    </div>
  );
}
