import { pageMissing } from '../builder/dealCardsModel';

/*
 * "Not printing" (plan.md §8.14; J112; the old ExportViewer usePagesNotPrinting at 891f1b3, D-189's page ledger): the
 * Presentation pages switched on that cannot print yet, from the builder's own ledger (re-read with every deal write),
 * each saying why; a click opens the proposal builder, whose Presentation pages card has its Fix ▸. A page the producer
 * switched off is a choice, not a gap, so it is not listed (the builder's `pageMissing`).
 */
export default function NotPrinting({ ledger, pages, onGoBuild }) {
  const missing = (ledger || []).filter((row) => pageMissing(row, pages || {}));
  if (!missing.length) return null;
  return (
    <div className="bnf-xv-ledger">
      <span className="bnf-xv-jump-label">Not printing</span>
      {missing.map((row) => (
        <button
          key={row.key}
          type="button"
          className="bnf-xv-chip"
          title={[
            row.why ? `${row.why[0].toUpperCase()}${row.why.slice(1)}.` : '',
            row.fix ? 'Put it right on the proposal builder.' : '',
          ]
            .filter(Boolean)
            .join(' ')}
          onClick={onGoBuild}
          disabled={!onGoBuild}
        >
          {row.label}
          <span className="bnf-xv-ledger-why"> ▸</span>
        </button>
      ))}
    </div>
  );
}
