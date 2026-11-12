import { FILL_WORDS, fillBar } from './lensModel';

function FillBar({ column }) {
  const bar = fillBar(column);
  if (!bar) {
    return (
      <span
        className="bb-muted"
        title="No row on this deal takes this column (a line we are not quoting, or employee-only)"
      >
        not asked here
      </span>
    );
  }
  return (
    <span
      className="bnf-lens-fill"
      title={`${bar.have} of the ${column.expected} rows this column applies to hold a value`}
    >
      <span className="bnf-lens-fillbar">
        <span
          className={`bnf-lens-fillbar-in${bar.short ? ' bnf-lens-fillbar-short' : ''}`}
          style={{ width: `${bar.pct}%` }}
        />
      </span>
      <span className={bar.short ? 'bb-rose' : ''}>
        {bar.have}/{column.expected}
      </span>
    </span>
  );
}

/*
 * Column by column (plan.md §8.12; K87; old CensusFormatLens.jsx at 891f1b3): the carrier's letter and header, what
 * fills it (our census, worked out, or nothing), the carrier's ★, how full it is over the rows it applies to, and how
 * it is written (the translation and the rules).
 */
export default function LensColumns({ columns }) {
  return (
    <div className="bb-grid-card bnf-lens-section" data-guide="census-lens-columns">
      <div className="bnf-lens-section-title">Column by column</div>
      <div className="bnf-lens-scroll">
        <table className="bnf-lens-table">
          <thead>
            <tr>
              <th>Col</th>
              <th>Their header</th>
              <th>What fills it</th>
              <th title="The carrier marks it required on their own sheet, or our export does">Required there</th>
              <th>Filled</th>
              <th>How it is written</th>
            </tr>
          </thead>
          <tbody>
            {columns.map((column, index) => (
              <tr key={`${column.letter}-${index}`} className={column.fills.kind === 'gap' ? 'bnf-lens-row-gap' : ''}>
                <td className="bb-mono">{column.letter}</td>
                <td>{column.header || <span className="bb-muted">(no header of its own)</span>}</td>
                <td>
                  <span className={`bnf-lens-kind bnf-lens-kind-${column.fills.kind}`}>
                    {FILL_WORDS[column.fills.kind] || column.fills.kind}
                  </span>{' '}
                  <span className="bnf-lens-fills">{column.fills.text}</span>
                </td>
                <td>{column.carrier_required ? '★' : ''}</td>
                <td>
                  <FillBar column={column} />
                </td>
                <td className="bnf-lens-rules">
                  {[column.translation, ...(column.rules || [])].filter(Boolean).join(' · ') || '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
