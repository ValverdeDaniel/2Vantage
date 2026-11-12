import { agoWords } from '../reviewModel';

function day(iso) {
  return iso ? new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : '';
}

/*
 * The bars around a section's queue (old 891f1b3 `CensusClientReview.jsx` `bnf-client-review-bar`, the in-progress
 * lines and `bnf-census-pager`): the phase tabs with their counts and when answers reach review; while showing what is
 * still being typed, who is typing and when it turns reviewable if nobody submits. `QueuePager` goes under the queue.
 */
export default function QueueBars({ meta, data, phase, onPhase }) {
  return (
    <>
      <div className="bnf-client-review-bar">
        <div className="bnf-advisor-views" role="group" aria-label="Phase">
          {(meta?.phases || []).map((entry) => (
            <button
              key={entry.key}
              type="button"
              className={`bnf-viewtab${phase === entry.key ? ' bnf-viewtab-on' : ''}`}
              aria-pressed={phase === entry.key}
              title={entry.title}
              onClick={() => phase !== entry.key && onPhase(entry.key)}
            >
              {entry.label} <span className="rr-pill-count">{data.phases[entry.key] || 0}</span>
            </button>
          ))}
        </div>
        <span className="bnf-review-note">
          Answers reach review when the client submits, or {data.idle_hours} hours after their last save.
        </span>
      </div>
      {phase === 'in_progress' && data.in_progress.length > 0 && (
        <div className="bnf-client-review-progress">
          {data.in_progress.map((link) => (
            <div key={link.link_id} className="bnf-client-review-link">
              <b>{link.name || 'The client'}</b> is still working on their link — saved{' '}
              {link.last_saved_at ? agoWords(link.last_saved_at) : 'earlier'}
              {link.ready_at ? `; ready to review ${day(link.ready_at)} if they never submit` : ''}.
            </div>
          ))}
        </div>
      )}
    </>
  );
}

/** The queue's pages, under it (old `bnf-census-pager`): 50 a page. */
export function QueuePager({ pages, onPage }) {
  if (pages.page_count <= 1) return null;
  return (
    <div className="bnf-census-pager">
      <button type="button" className="btn btn-secondary btn-sm" disabled={!pages.has_prev} onClick={() => onPage(pages.page - 1)}>
        ‹ Back
      </button>
      <span className="bnf-census-pager-label">
        Page {pages.page} of {pages.page_count}
      </span>
      <button type="button" className="btn btn-secondary btn-sm" disabled={!pages.has_next} onClick={() => onPage(pages.page + 1)}>
        Next ›
      </button>
    </div>
  );
}
