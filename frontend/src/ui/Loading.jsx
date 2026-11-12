/**
 * The old first-load panel (`loading bnf-load-panel`, plan.md §8.22) with its words: "Loading the deal…".
 * A refetch keeps the data on screen and shows RefreshChip instead.
 */
export default function Loading({ label = 'Loading...', note }) {
  return (
    <div className="loading bnf-load-panel" role="status">
      <div className="bnf-load-panel-title">{label}</div>
      {note && <div className="bnf-load-panel-note">{note}</div>}
    </div>
  );
}
