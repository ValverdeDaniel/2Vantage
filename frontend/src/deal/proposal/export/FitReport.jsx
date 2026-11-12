/*
 * The fit report above a plan set's slide (plan.md §8.14; J110; the old ExportViewer fit strip at 891f1b3, D-193 slice
 * 3): green when the table sits on one slide, amber when its notes moved on, it sits at the smallest type or rows run
 * past two lines, red when it ran on or its rates and totals start apart from its benefits (`deckModel.fitVerdict`).
 */
export default function FitReport({ verdict }) {
  if (!verdict) return null;
  return (
    <div className={`bnf-xv-fit bnf-xv-fit-${verdict.level}`} role="status">
      <div>{verdict.words}</div>
      {verdict.tall.length > 0 && <div className="bnf-xv-fit-tall">Rows over two lines: {verdict.tall.join(', ')}</div>}
    </div>
  );
}
