/*
 * The strips around the roster grid (plan.md §8.10; C1, C2, C8; the old CensusGrid at 891f1b3, its words and
 * classes): the ☑ Select cells bar, the line chips, and the pager by employee.
 */

/** ☑ Select cells' bar (C8): the count, ✓ Approve, Ignore, ⚑ Needs checking on the picked cells that hold a value,
 * and ＋ Ask N (the request tray arrives with Review & requests). */
export function SelectBar({ count, filled, busy, onMark }) {
  const off = !filled || Boolean(busy);
  return (
    <div className="bb-select-bar">
      <div>
        Click cells to pick them: approve, ignore or flag them, or ask the client.{' '}
        <span className="bb-select-hint">Use “Select all missing” for a head start.</span>
      </div>
      <div className="bb-select-bar-right">
        <div className="bb-select-count">{count} selected</div>
        <button
          type="button"
          className="bb-btn-white"
          disabled={off}
          title="The selected values are right as read: approve them"
          onClick={() => onMark('approve')}
        >
          ✓ Approve
        </button>
        <button
          type="button"
          className="bb-btn-white"
          disabled={off}
          title="Leave the selected values as read and stop warning about them"
          onClick={() => onMark('ignore')}
        >
          Ignore
        </button>
        <button
          type="button"
          className="bb-btn-white"
          disabled={off}
          title="Flag the selected values for a second look"
          onClick={() => onMark('check')}
        >
          ⚑ Needs checking
        </button>
        <button
          type="button"
          className="bb-btn-white"
          disabled
          title="Asking the client goes through the request tray, which arrives with Review & requests"
        >
          ＋ Ask {count || ''}
        </button>
      </div>
    </div>
  );
}

/** The line chips (C2): Person & employment always on; each line group on or off. */
export function LineChips({ groups, hidden, onToggle }) {
  if (groups.length < 2) return null;
  return (
    <div className="bnf-line-chips">
      <span className="bnf-line-chips-label">Columns</span>
      <span className="bb-chip bnf-chip-locked" title="Always shown">
        Person &amp; employment
      </span>
      {groups.map((group) => (
        <button
          key={group.key}
          type="button"
          className={`bb-chip ${hidden.has(group.key) ? '' : 'active'}`}
          aria-pressed={!hidden.has(group.key)}
          onClick={() => onToggle(group.key)}
        >
          {group.label}
        </button>
      ))}
    </div>
  );
}

/** "Employees 101–152 of 152 · page 2 of 2" with ‹ Previous and Next › (C1: paged by employee). */
export function Pager({ page, onPage }) {
  if (!page || page.pages <= 1) return null;
  const first = (page.number - 1) * page.page_size + 1;
  const last = Math.min(page.number * page.page_size, page.employees);
  return (
    <div className="bnf-census-pager">
      <button
        type="button"
        className="btn btn-secondary btn-sm"
        disabled={page.number <= 1}
        onClick={() => onPage(page.number - 1)}
      >
        ‹ Previous
      </button>
      <span className="bnf-census-pager-label">
        Employees {first}–{last} of {page.employees}
        <span className="bnf-census-pager-note">
          {' '}
          · page {page.number} of {page.pages}
        </span>
      </span>
      <button
        type="button"
        className="btn btn-secondary btn-sm"
        disabled={page.number >= page.pages}
        onClick={() => onPage(page.number + 1)}
      >
        Next ›
      </button>
    </div>
  );
}
