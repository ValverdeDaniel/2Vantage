/*
 * "Sent earlier" (plan.md §5.7; K120, bug 35): a send whose draft no longer exists — the route or the picks changed —
 * still counts as asked (Markets checked lists it), so it stays listed with its date and an Undo that takes it back.
 */
export default function SentEarlier({ rows, sending, onUndo }) {
  if (!rows?.length) return null;
  return (
    <div className="bnf-rfp-rownote" data-guide="rfp-sent-earlier">
      <b>Sent earlier</b> — these emails went out before the picks or the route changed, and still count as asked:
      {rows.map((row) => (
        <div key={row.key}>
          {row.label} · {row.shown}
          {row.by ? ` · ${row.by}` : ''}{' '}
          <button type="button" className="bnf-override-link" disabled={sending} onClick={() => onUndo(row.key)}>
            Undo
          </button>
        </div>
      ))}
    </div>
  );
}
