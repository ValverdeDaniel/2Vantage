/*
 * "⧉ One column with…" and Split in a column's ⋯ More (plan.md §5.4, §8.14; D-219, J15; slice 33; the old
 * ProposalPlansCard.jsx `mergeControl` at 891f1b3). The server says which state the plan is in (`plan.pair`,
 * proposals/page_pairs.py): paired (its partner, with Split), following its current pair (a renewal, no Split), or the
 * plans it may print as one column with (one carrier, one kind, in no pair). Both plans stay in the data; the client
 * files print one column worked out from both.
 */
export default function PairControl({ plan, busy, onPair, onSplit }) {
  const pair = plan.pair;
  if (!pair) return null;
  if (pair.state === 'paired') {
    return (
      <span className="bnf-pp-merged" title={pair.title}>
        ⧉ One column with {pair.with}{' '}
        <button type="button" className="bnf-override-link" disabled={busy} onClick={() => onSplit(plan)}>
          Split
        </button>
      </span>
    );
  }
  if (pair.state === 'follows') {
    return (
      <span className="bnf-pp-merged" title={pair.title}>
        ⧉ One column with {pair.with}
      </span>
    );
  }
  return (
    <select
      className="filter-select bnf-pp-merge"
      value=""
      disabled={busy}
      aria-label={`Print ${plan.name} as one column with another plan`}
      title={pair.title}
      onChange={(event) => {
        const other = Number(event.target.value);
        if (other) onPair(plan, other);
      }}
    >
      <option value="">⧉ One column with…</option>
      {pair.choices.map((other) => (
        <option key={other.id} value={other.id}>
          {other.name}
        </option>
      ))}
    </select>
  );
}
