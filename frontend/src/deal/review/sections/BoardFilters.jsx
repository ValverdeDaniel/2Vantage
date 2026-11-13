import { toggled } from './boardModel';

/** An origin's dot in its tone (reviewrequest.css `rr-origin-dot rr-tone-*`; D-060). */
export function OriginDot({ origin }) {
  if (!origin) return null;
  return <span className={`rr-origin-dot rr-tone-${origin.tone}`} aria-hidden="true" />;
}

/*
 * The filters above a section's board (plan.md §8.8; B37, C27; old 891f1b3 `IntakeReviewView.jsx` and
 * `CensusReviewView.jsx` `bnf-advisor-filtercard`): a row of group (or section) chips, the status chips, where the values
 * came from, a search and the checks; "N active · Clear". The words come from /api/meta/ `review`.
 */
export function BoardFilters({ filters, active, onChange, onClear, groups, groupKey, statuses, origins, originCounts, checks, searchWords }) {
  return (
    <div className="bnf-advisor-filtercard bnf-wq-filters bnf-ireview-filters">
      <div className="bnf-advisor-filtercard-head">
        <span className="bnf-review-note">Filter the board</span>
        <span className="bnf-advisor-filterstate">
          {active > 0 && (
            <>
              <b>{active}</b> active{' '}
              <button type="button" className="bnf-advisor-clear" onClick={onClear}>
                Clear
              </button>
            </>
          )}
        </span>
      </div>
      <div className="bnf-advisor-labelrow">
        {groups.map((group) => (
          <button key={group.key || 'all'} type="button" className={`bnf-wq-chip${filters[groupKey] === group.key ? ' bnf-wq-chip-on' : ''}`}
            onClick={() => onChange({ [groupKey]: group.key })}>
            {group.label}
            {group.count ? ` · ${group.count}` : ''}
          </button>
        ))}
      </div>
      <div className="bnf-advisor-labelrow">
        <span className="bnf-review-note">Status</span>
        {(statuses || []).map((status) => (
          <button key={status.key} type="button" className={`bnf-wq-chip${filters.statuses.includes(status.key) ? ' bnf-wq-chip-on' : ''}`}
            onClick={() => onChange({ statuses: toggled(filters.statuses, status.key) })}>
            {status.label}
          </button>
        ))}
      </div>
      {origins.length > 0 && (
        <div className="bnf-advisor-labelrow">
          <span className="bnf-review-note">Where it came from</span>
          {origins.map((origin) => (
            <button key={origin.key} type="button" title={origin.label}
              className={`bnf-wq-chip${filters.origins.includes(origin.key) ? ' bnf-wq-chip-on' : ''}`}
              onClick={() => onChange({ origins: toggled(filters.origins, origin.key) })}>
              <OriginDot origin={origin} /> {origin.short} · {originCounts[origin.key] || 0}
            </button>
          ))}
        </div>
      )}
      <div className="bnf-advisor-labelrow">
        <input className="bnf-review-search" placeholder={searchWords} value={filters.search} aria-label={searchWords}
          onChange={(event) => onChange({ search: event.target.value })} />
        {checks.map(([key, words]) => (
          <label key={key} className="bnf-review-check">
            <input type="checkbox" checked={filters[key]} onChange={(event) => onChange({ [key]: event.target.checked })} />
            {words}
          </label>
        ))}
      </div>
    </div>
  );
}
