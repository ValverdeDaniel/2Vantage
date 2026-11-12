import { useEffect, useRef, useState } from 'react';
import { statusChips } from './homeParams';

/**
 * The filter card above the list (`bnf-wq-filters`, I78's look): on Clients the Status chips All · New clients ·
 * Existing clients (CL12), and the client search, which asks the server 250 ms after typing stops (§8.3). The box
 * shows the URL's text otherwise, so Back restores it. I78's due, owner and stage filters wait for slice 61.
 */
export default function HomeSearch({ view, q, status, statuses, onChange }) {
  const [draft, setDraft] = useState(null);
  const timer = useRef(null);
  useEffect(() => () => clearTimeout(timer.current), []);

  function type(text) {
    setDraft(text);
    clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      onChange({ q: text }, { replace: true });
      setDraft(null);
    }, 250);
  }

  function clear() {
    clearTimeout(timer.current);
    setDraft(null);
    onChange({ q: '' }, { replace: true });
  }

  const shown = draft ?? q;
  return (
    <div className="bnf-wq-filters">
      <div className="bnf-wq-toprow">
        <div className="bnf-wq-chipcol">
          {view === 'book' && (
            <div className="bnf-wq-chiprow" role="group" aria-label="Status">
              <span className="bnf-wq-filterlabel">Status</span>
              {statusChips(statuses).map((chip) => (
                <button
                  key={chip.key || 'all'}
                  type="button"
                  aria-pressed={status === chip.key}
                  className={status === chip.key ? 'bnf-wq-chip bnf-wq-chip-on' : 'bnf-wq-chip'}
                  onClick={() => onChange({ status: chip.key })}
                >
                  {chip.label}
                </button>
              ))}
            </div>
          )}
        </div>
        <div className="bnf-wq-search">
          <input
            type="text"
            placeholder="Search clients…"
            aria-label="Search clients"
            value={shown}
            onChange={(event) => type(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Escape' && shown) clear();
            }}
          />
          {shown && (
            <button type="button" className="bnf-wq-search-x" aria-label="Clear client search" onClick={clear}>
              ×
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
