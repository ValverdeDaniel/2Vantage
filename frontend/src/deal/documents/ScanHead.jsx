/*
 * The Scanned data panel's head (plan.md §8.16; E34, E35; the old DocumentsTab's `bnf-scan-head`): "Scanned data ·
 * Proposal · all N files", the quality headline with its high / review / missing chips — counted by the server over
 * the plans these files gave (`head` is the List's first page, or null off a proposal file) — and the buttons.
 */
export default function ScanHead({ scope, head, children }) {
  const quality = head?.quality;
  return (
    <div className="bnf-scan-head">
      <div className="bb-panel-title">
        Scanned data
        {scope.label && <span className="bnf-scan-sub"> · {scope.label}</span>}
        {scope.ids.length > 1 && <span className="bnf-scan-sub"> · all {scope.ids.length} files</span>}
      </div>
      {head && (
        <div className="bnf-quality">
          <span className={`bnf-quality-label bb-${head.headline.tone}`}>{head.headline.label}</span>
          {(quality.high > 0 || quality.low > 0 || quality.missing > 0) && (
            <span className="bnf-quality-chips">
              {quality.high > 0 && <span className="bb-badge bb-badge-green">{quality.high} high</span>}
              {quality.low > 0 && <span className="bb-badge bb-badge-amber">{quality.low} review</span>}
              {quality.missing > 0 && <span className="bb-badge bb-badge-rose">{quality.missing} missing</span>}
            </span>
          )}
        </div>
      )}
      {children}
    </div>
  );
}
