/*
 * Where an SBC and a quote disagree (plan.md §10.4; D47; slice 22; the old StagedScanReview's SbcSections): the SBC's
 * value is the one kept, flagged for a look, and a value someone typed still wins. `conflicts` comes with the SBC
 * read's change set: [{item, plan, label, quote, sbc, kept}].
 */
export default function SbcNotes({ conflicts }) {
  if (!conflicts?.length) return null;
  return (
    <div className="bnf-staged-section" data-sbc-conflicts>
      <div className="bnf-staged-section-title">Where the SBC and the quote disagree</div>
      <div className="bnf-staged-section-sub">
        The SBC&apos;s value is kept and flagged for a look. A value you typed still wins.
      </div>
      <ul className="bnf-staged-list">
        {conflicts.map((row) => (
          <li key={`${row.item}-${row.key}`}>
            {row.plan} · {row.label}: {row.kept ? 'on the plan' : 'quote said'} {row.quote || '—'}; SBC says{' '}
            {row.sbc || '—'}
            {row.kept ? ` (${row.kept}: it stays unless you tick it)` : ''}
          </li>
        ))}
      </ul>
    </div>
  );
}
