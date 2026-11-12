import { notSentWords } from './lensModel';

/*
 * What they ask that we don't store (plan.md §8.12; K88; old CensusFormatLens.jsx at 891f1b3): each gap with where its
 * answer would live and what to weigh; the notes on what we answer only partly; and, folded, the columns the carrier
 * prints that we never write (UHC's enrollment half), saying which are their own formulas.
 */
export default function LensGaps({ detail }) {
  const notSent = detail.not_sent?.columns || [];
  return (
    <div className="bb-panel bnf-lens-section" data-guide="census-lens-gaps">
      <div className="bnf-lens-section-title">What they ask that we don&apos;t store</div>
      {detail.gaps.length === 0 ? (
        <div>Nothing missing — every column they ask for, we can fill.</div>
      ) : (
        <ul className="bnf-lens-gaps">
          {detail.gaps.map((gap) => (
            <li key={gap.header}>
              <b>{gap.header}</b>
              {gap.home && <span className="bnf-lens-home"> · {gap.home}</span>}
              {gap.note && <div className="bnf-review-note">{gap.note}</div>}
            </li>
          ))}
        </ul>
      )}
      {(detail.gap_notes || []).map((note) => (
        <div key={note} className="bnf-review-note">
          {note}
        </div>
      ))}
      {notSent.length > 0 && (
        <details className="bnf-lens-unwritten">
          <summary>Printed on their sheet, never sent — {notSentWords(detail.not_sent)}</summary>
          <ul>
            {notSent.map((column) => (
              <li key={column.letter}>
                <span className="bb-mono">{column.letter}</span> {column.header}
                {column.formula && <span className="bnf-lens-home"> · their formula</span>}
                {column.note && <div className="bnf-review-note">{column.note}</div>}
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
