/*
 * The rest of a quote read's change set (plan.md §10.5; D31, OQ30; the old ProposedChangesCard's rows): the tier
 * counts the file prints, proposed unticked — per current plan, or as the line's figure (O.6 #10) — and the lines no
 * one asked for (D56), each with its tick, page and why; then the plans from these files the read did not return.
 */
export default function ChangeList({ items, kept, picked, onToggle }) {
  const counts = items.filter((item) => item.op === 'summary_counts');
  const lines = items.filter((item) => item.op === 'add_lines');
  if (!counts.length && !lines.length && !kept?.length) return null;
  return (
    <div className="bnf-pchg bb-mt" data-review-changes>
      {counts.length > 0 && (
        <div className="bnf-pchg-section">
          <div className="bnf-pchg-section-title">Tier counts printed in the file</div>
          <div className="bnf-pchg-section-note">
            Never a plan&apos;s own counts until you tick them: they price the plan only once used.
          </div>
        </div>
      )}
      <div className="bnf-pchg-list">
        {[...counts, ...lines].map((item) => (
          <label key={item.id} className="bnf-pchg-row" data-item={item.id} title={item.why}>
            <input type="checkbox" checked={picked.has(item.id)} onChange={() => onToggle(item.id)} />
            <span className="bnf-pchg-field">{item.op === 'add_lines' ? 'Add lines' : item.label}</span>
            <span className="bnf-pchg-values">
              <span className="bnf-pchg-new">{item.op === 'add_lines' ? item.label : item.text}</span>
            </span>
            <span className="bnf-pchg-meta">
              {item.page ? `p.${item.page} · ` : ''}
              {item.tick ? '' : 'unticked · '}
              {item.why}
            </span>
          </label>
        ))}
      </div>
      {kept?.length > 0 && (
        <div className="bnf-staged-section">
          <div className="bnf-staged-section-title">Not in this read — kept</div>
          <ul className="bnf-staged-list">
            {kept.map((row) => (
              <li key={row.plan}>{row.label}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
