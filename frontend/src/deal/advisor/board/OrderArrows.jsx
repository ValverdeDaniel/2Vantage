/*
 * The arrows that move a plan one place in the client's order (plan.md §8.14; F43, F44, OQ13; the old OrderArrows.jsx):
 * ◀ ▶ where the plans run left to right (transposed), ▲ ▼ down the rows. On every line, stop-loss included. Each
 * writes through the order door; the board, the builder and every document read the same order.
 */
export default function OrderArrows({ name, axis = 'y', first = false, last = false, busy = false, onMove }) {
  const [back, ahead] = axis === 'x' ? ['◀', '▶'] : ['▲', '▼'];
  const earlier = axis === 'x' ? 'Show it further left' : 'Show it earlier';
  const later = axis === 'x' ? 'Show it further right' : 'Show it later';
  return (
    <span className="bnf-order-arrows">
      <button
        type="button"
        className="bnf-build-order-btn"
        disabled={busy || first}
        title={`${earlier}: here, on the proposal and in the documents`}
        aria-label={`Move ${name} earlier`}
        onClick={(event) => {
          event.stopPropagation();
          onMove(-1);
        }}
      >
        {back}
      </button>
      <button
        type="button"
        className="bnf-build-order-btn"
        disabled={busy || last}
        title={`${later}: here, on the proposal and in the documents`}
        aria-label={`Move ${name} later`}
        onClick={(event) => {
          event.stopPropagation();
          onMove(1);
        }}
      >
        {ahead}
      </button>
    </span>
  );
}
