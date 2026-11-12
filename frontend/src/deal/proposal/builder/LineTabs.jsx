import cx from '../../../ui/cx';

/*
 * The builder's line tabs (plan.md §8.14; J31; the old `bnf-lineswitch` at 891f1b3): ✓ when every card on the line is
 * marked completed, "off" for a line the intent keeps off, the state chip (guaranteed / new) or the count of plans on
 * the proposal, and ◀ ▶ for the line's place in the proposal (`config.order`). Shown with two or more lines.
 */
export default function LineTabs({ lines, line, busy, onPick, onMove }) {
  if (lines.length < 2) return null;
  const at = lines.findIndex((entry) => entry.line === line);
  return (
    <div className="bnf-lineswitch" data-guide="build-lines">
      {lines.map((entry) => (
        <button
          key={entry.line}
          type="button"
          className={cx('bnf-linetab', entry.line === line && 'bnf-linetab-on')}
          title={entry.chip?.title}
          onClick={() => onPick(entry.line)}
        >
          {entry.done && (
            <span className="bnf-linetab-done" title="Every card on this line is marked completed">
              ✓
            </span>
          )}
          {entry.label}
          {entry.off && (
            <span className="bnf-state-chip bnf-state-off" title={entry.off.words}>
              off
            </span>
          )}
          {entry.chip ? (
            <span className={`bnf-state-chip bnf-state-${entry.chip.tone}`}>{entry.chip.text}</span>
          ) : (
            <span className="bnf-linetab-count">{entry.presented_ids.length}</span>
          )}
        </button>
      ))}
      <span className="bnf-build-order" data-guide="build-line-order">
        <span className="bnf-advisor-views-label">Order</span>
        <button
          type="button"
          className="bnf-build-order-btn"
          disabled={busy || at <= 0}
          title="Move this line earlier in the proposal"
          onClick={() => onMove(line, -1)}
        >
          ◀
        </button>
        <button
          type="button"
          className="bnf-build-order-btn"
          disabled={busy || at === lines.length - 1}
          title="Move this line later in the proposal"
          onClick={() => onMove(line, 1)}
        >
          ▶
        </button>
      </span>
    </div>
  );
}
