/**
 * The old "Refreshing…" chip (ComparisonStatus.jsx at 891f1b3; plan.md §8.22): data stays on screen while a newer
 * copy loads, or says the refresh failed with Retry. Renders nothing otherwise.
 */
export default function RefreshChip({ loading, error, onRetry, label = 'Refreshing…' }) {
  if (loading) {
    return (
      <span className="bnf-refresh-chip" role="status">
        <span className="bnf-refresh-dot" aria-hidden="true" />
        {label}
      </span>
    );
  }
  if (error) {
    return (
      <span className="bnf-refresh-chip bnf-refresh-chip-failed" role="status">
        Couldn&apos;t refresh, so this is the last copy ·{' '}
        <button type="button" className="bnf-refresh-retry" onClick={onRetry}>
          Retry
        </button>
      </span>
    );
  }
  return null;
}
