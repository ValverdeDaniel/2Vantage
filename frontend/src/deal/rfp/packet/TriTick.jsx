import { countWords, includeBody, triState } from './packetModel';

/*
 * A three-state box over some rows (plan.md §8.12; K35; old CarriersTab.jsx TriTick at 891f1b3): ticked when every
 * carrier-facing row is in, dashed when some are, empty when none are. Clicking it selects all (or, when everything is
 * in, deselects all); Select all and Deselect all beside it. Only disagreements with the recommendation are sent.
 */
export default function TriTick({ rows, onSet, label = '', guide }) {
  const state = triState(rows);
  if (!state.total) return null;
  const set = (value) => {
    const body = includeBody(state.eligible, value);
    if (Object.keys(body).length) onSet(body);
  };
  return (
    <span className="bnf-rfp-tritick" data-guide={guide}>
      <input
        type="checkbox"
        checked={state.all}
        ref={(el) => {
          if (el) el.indeterminate = state.some;
        }}
        title={state.all ? 'Take everything out of the packet' : 'Tick every carrier-facing document'}
        aria-label={label || 'Every row in this section'}
        onChange={() => set(!state.all)}
      />
      {label && <span className="bnf-rfp-tritick-label">{label}</span>}
      <span className="bnf-rfp-section-count">{countWords(state)}</span>
      <button type="button" className="bnf-override-link" disabled={state.all} onClick={() => set(true)}>
        Select all
      </button>
      <span className="bnf-rfp-section-sep">·</span>
      <button type="button" className="bnf-override-link" disabled={state.on === 0} onClick={() => set(false)}>
        Deselect all
      </button>
    </span>
  );
}
