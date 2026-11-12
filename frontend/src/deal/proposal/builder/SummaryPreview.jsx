/*
 * "On the proposal right now" (plan.md §8.14; J64; the old `bnf-build-preview` at 891f1b3, same classes): every
 * picked figure as the server worked it out (`summary.blocks`), or the reason it cannot be, so the producer sees why a
 * figure is not on the page. Each figure arrives formatted (value, change, sub-line); the files print only the
 * available ones.
 */
export default function SummaryPreview({ blocks }) {
  return (
    <div className="bnf-build-preview" data-guide="build-preview">
      <div className="bnf-build-rowgroup-title">On the proposal right now</div>
      {blocks.length === 0 && <div className="bb-empty">Nothing to show yet.</div>}
      {blocks.map((block, i) => (
        <div
          key={`${block.key}-${block.line}-${i}`}
          className={`bnf-build-stat ${block.available ? '' : 'bnf-build-stat-off'}`}
        >
          <span className="bnf-build-stat-label">
            {block.line_label ? `${block.line_label} · ` : ''}
            {block.label}
          </span>
          {block.available ? (
            <span className="bnf-build-stat-value">
              {block.value_label}
              {block.delta_label && (
                <em className={`bnf-delta ${block.delta_dir === 'good' ? 'bnf-delta-neg' : 'bnf-delta-pos'}`}>
                  {block.delta_label}
                </em>
              )}
              {block.sub && <i className="bb-drop-meta">{block.sub}</i>}
            </span>
          ) : (
            <span className="bnf-build-stat-off-why">{block.reason}</span>
          )}
        </div>
      ))}
    </div>
  );
}
