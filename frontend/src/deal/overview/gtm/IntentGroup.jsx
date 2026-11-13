import { formatDate } from '../../../lib/format';

/**
 * Coverage & marketing intent, read-only (M45; old 891f1b3 `GetToMarketCard.jsx`): each line Shopping or Not shopped,
 * "· new line", "· on the proposal", "· guaranteed to <date>"; then Open (or Changed, when what was confirmed no
 * longer matches) with intake's words, or "✓ Confirmed by <name>". The decisions are made on the Intake tab's card.
 */
export default function IntentGroup({ group }) {
  return (
    <>
      {group.lines.map((line) => (
        <div key={line.line} className="bnf-req-line">
          <span className={`bb-badge ${line.shopping ? 'bb-badge-green' : 'bb-badge-gray'}`}>
            {line.shopping ? 'Shopping' : 'Not shopped'}
          </span>
          {line.label}
          {!line.in_force && ' · new line'}
          {line.on_proposal && !line.shopping && ' · on the proposal'}
          {line.guaranteed_to && ` · guaranteed to ${formatDate(line.guaranteed_to)}`}
        </div>
      ))}
      {group.lines.length === 0 && (
        <div className="bnf-req-line">
          <span className="bb-badge bb-badge-rose">Missing</span>
          No coverage recorded yet
        </div>
      )}
      {group.met ? (
        <div className="bnf-req-line">
          <span className="bb-check">✓</span>
          Confirmed{group.confirmed_by ? ` by ${group.confirmed_by}` : ''}
        </div>
      ) : (
        <div className="bnf-req-line">
          <span className={`bb-badge ${group.stale ? 'bb-badge-amber' : 'bb-badge-rose'}`}>{group.stale ? 'Changed' : 'Open'}</span>
          {group.detail}
        </div>
      )}
    </>
  );
}
