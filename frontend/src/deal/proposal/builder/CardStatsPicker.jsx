import { moved } from './builderModel';

/*
 * "On the plan cards" (plan.md §8.14; J61; the old `bnf-build-cardstats` at 891f1b3): a plan's headline stats, up to
 * six, in order — ▲ ▼ to reorder, ✕ to take one off, "Add a stat…" from the line's client rows, and "standard" back to
 * the field set's list. The resolved list (the pick, or the standard set) is the server's, so the picker always starts
 * from what the client sees; an edit stores the whole list (`lines.<line>.card_stats`; null is the standard set).
 */
export default function CardStatsPicker({ line, max, busy, onChange }) {
  const stats = line.card_stats;
  const keys = stats.map((stat) => stat.key);
  const move = (i, dir) => {
    const next = moved(keys, i, dir);
    if (next) onChange(next);
  };
  return (
    <div className="bnf-build-cardstats" data-guide="build-card-stats">
      <div className="bnf-build-rowshead">
        <span className="bnf-build-rowgroup-title">On the plan cards</span>
        {!line.card_stats_standard && (
          <span className="bnf-build-selectall">
            <button type="button" disabled={busy} title="Back to this line's standard stats" onClick={() => onChange(null)}>
              standard
            </button>
          </span>
        )}
      </div>
      <div className="bnf-build-chosen">
        {stats.map((stat, i) => (
          <div key={stat.key} className="bnf-build-chosen-row">
            <button
              type="button"
              className="bnf-build-order-btn"
              disabled={busy || i === 0}
              title="Move up"
              aria-label={`Move ${stat.label} up`}
              onClick={() => move(i, -1)}
            >
              ▲
            </button>
            <button
              type="button"
              className="bnf-build-order-btn"
              disabled={busy || i === stats.length - 1}
              title="Move down"
              aria-label={`Move ${stat.label} down`}
              onClick={() => move(i, 1)}
            >
              ▼
            </button>
            <span className="bnf-build-chosen-label">{stat.label}</span>
            <button
              type="button"
              className="bnf-build-order-btn"
              disabled={busy || stats.length === 1}
              title="Take it off the cards"
              aria-label={`Take ${stat.label} off the cards`}
              onClick={() => onChange(keys.filter((key) => key !== stat.key))}
            >
              ✕
            </button>
          </div>
        ))}
      </div>
      {keys.length < max && (
        <select
          className="filter-select bnf-build-cardstats-add"
          disabled={busy}
          value=""
          aria-label="Add a stat to the plan cards"
          onChange={(event) => event.target.value && onChange([...keys, event.target.value])}
        >
          <option value="">Add a stat…</option>
          {line.rows
            .filter((row) => !keys.includes(row.key))
            .map((row) => (
              <option key={row.key} value={row.key}>
                {row.label}
              </option>
            ))}
        </select>
      )}
      <div className="bb-drop-meta">
        Each plan&apos;s card shows these, and so do the plan highlights in the PDF recommendation. Up to six.
      </div>
    </div>
  );
}
