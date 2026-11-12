import { todoStatus } from './portalModel';

/*
 * "Your to-do list" (plan.md §8.20; L81). Ported from old Vantage 891f1b3 `PortalChecklist`: a row per section with
 * its count or state, the progress bar, and a click that scrolls to the section (`bnf-sec-<key>`). On a phone the
 * rail sits above the form (the old sheet's single column under 860 px).
 */
export default function TodoRail({ rail }) {
  if (!rail || rail.total === 0) return null;
  const pct = Math.round((rail.done / rail.total) * 100);
  return (
    <div className="bb-portal-card bnf-todo-card">
      <div className="bnf-progress-row">
        <span className="bnf-progress-label">Your to-do list</span>
        <span className="bnf-progress-count">
          {rail.done} of {rail.total} complete
        </span>
      </div>
      <div className="bnf-progress-track">
        <div className="bnf-progress-fill" style={{ width: `${pct}%` }} />
      </div>
      <div className="bnf-todo-items">
        {rail.items.map((item) => (
          <button
            key={item.key}
            type="button"
            className={`bnf-todo-item ${item.done ? 'bnf-todo-item-done' : ''}`}
            onClick={() =>
              document.getElementById(`bnf-sec-${item.key}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
            }
          >
            <span className="bnf-todo-check">{item.done ? '✓' : '○'}</span>
            <span className="bnf-todo-label">{item.label}</span>
            <span className={`bnf-todo-count ${item.staged ? 'bnf-todo-staged' : ''}`}>{todoStatus(item)}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
