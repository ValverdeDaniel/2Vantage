import { useEffect, useMemo, useRef, useState } from 'react';
import { stageLabel } from '../../api/meta';
import { clientOptions } from './homeRows';

/*
 * The filter card over Prospects and the Work queue (A11, I78, I79; old HomeFilters.jsx at 891f1b3): Type chips (the
 * queue only), Responses first, Due chips, the client search with its ranked dropdown, Owner, Stage, Category (the
 * queue only) and Clear filters. The values live in the page (both views read them); only the dropdown's open state
 * lives here. Chips, stages and categories come from /api/meta/ (rule 1).
 */
export default function QueueFilters({
  mode,
  meta,
  filters,
  onChange,
  onClear,
  owners,
  clientNames,
  liftResponses,
  onLiftResponses,
  waitingCount,
}) {
  const { type, due, owner, stage, category, selectedClient, clientQuery } = filters;
  const queue = meta.agenda?.queue || {};
  const isQueue = mode === 'queue';
  const [searchOpen, setSearchOpen] = useState(false);
  const searchRef = useRef(null);

  useEffect(() => {
    if (!searchOpen) return undefined;
    const onDown = (event) => {
      if (searchRef.current && !searchRef.current.contains(event.target)) setSearchOpen(false);
    };
    document.addEventListener('mousedown', onDown);
    return () => document.removeEventListener('mousedown', onDown);
  }, [searchOpen]);

  const options = useMemo(() => clientOptions(clientNames, clientQuery), [clientNames, clientQuery]);
  const pickClient = (name) => {
    onChange({ selectedClient: name, clientQuery: name });
    setSearchOpen(false);
  };
  const filtered =
    due !== 'all' ||
    owner !== 'all' ||
    stage !== 'all' ||
    selectedClient ||
    (isQueue && (type !== 'all' || category !== 'all'));

  const chips = (label, list, value, key) => (
    <div className="bnf-wq-chiprow" role="group" aria-label={label}>
      <span className="bnf-wq-filterlabel">{label}</span>
      {list.map((chip) => (
        <button
          key={chip.key}
          type="button"
          aria-pressed={value === chip.key}
          className={value === chip.key ? 'bnf-wq-chip bnf-wq-chip-on' : 'bnf-wq-chip'}
          onClick={() => onChange({ [key]: chip.key })}
        >
          {chip.label}
        </button>
      ))}
    </div>
  );

  return (
    <div className="bnf-wq-filters">
      <div className="bnf-wq-toprow">
        <div className="bnf-wq-chipcol">
          {isQueue && chips('Type', queue.types || [], type, 'type')}
          <div className="bnf-wq-chiprow">
            <span className="bnf-wq-filterlabel">Client responses</span>
            <button
              type="button"
              aria-pressed={liftResponses}
              className={`bnf-wq-chip bnf-responses-toggle ${liftResponses ? 'bnf-wq-chip-on' : ''}`}
              title={
                liftResponses
                  ? 'Back to the table’s own order'
                  : 'Lift the deals waiting on us to the top: unanswered questions and answers to review, then the ones still answering, then the ones we have answered'
              }
              onClick={() => onLiftResponses(!liftResponses)}
            >
              {liftResponses ? '✓ ' : ''}Responses first
              {waitingCount > 0 && <span className="bnf-responses-count">{waitingCount} waiting on us</span>}
            </button>
          </div>
          {chips('Due', queue.due || [], due, 'due')}
        </div>
        <div className="bnf-wq-search" ref={searchRef}>
          <input
            type="text"
            placeholder="Search clients…"
            aria-label="Search clients"
            value={clientQuery}
            onFocus={() => setSearchOpen(true)}
            onChange={(event) => {
              onChange({ clientQuery: event.target.value, ...(selectedClient ? { selectedClient: null } : {}) });
              setSearchOpen(true);
            }}
            onKeyDown={(event) => {
              if (event.key === 'Escape') setSearchOpen(false);
            }}
          />
          {(selectedClient || clientQuery) && (
            <button
              type="button"
              className="bnf-wq-search-x"
              aria-label="Clear client search"
              onClick={() => onChange({ selectedClient: null, clientQuery: '' })}
            >
              ×
            </button>
          )}
          {searchOpen && (
            <div className="bnf-wq-search-menu">
              {options.map((name) => (
                <button key={name} type="button" onClick={() => pickClient(name)}>
                  {name}
                </button>
              ))}
              {options.length === 0 && <div className="bnf-wq-search-empty">No clients match</div>}
            </div>
          )}
        </div>
      </div>
      <div className="bnf-wq-selects">
        <select aria-label="Owner" value={owner} onChange={(event) => onChange({ owner: event.target.value })}>
          <option value="all">All owners</option>
          {owners.map((person) => (
            <option key={person.id} value={person.id}>
              {person.name}
            </option>
          ))}
          <option value="none">Unassigned</option>
        </select>
        <select
          aria-label="Stage"
          value={stage}
          onChange={(event) =>
            onChange({ stage: event.target.value, ...(event.target.value !== 'all' ? { category: 'all' } : {}) })
          }
        >
          <option value="all">All stages</option>
          {(meta.stages || []).map((item) => (
            <option key={item.key} value={item.key}>
              {stageLabel(meta, item.key)}
            </option>
          ))}
        </select>
        {isQueue && (
          <select
            aria-label="Category"
            value={category}
            onChange={(event) =>
              onChange({ category: event.target.value, ...(event.target.value !== 'all' ? { stage: 'all' } : {}) })
            }
          >
            <option value="all">All categories</option>
            {(queue.categories || []).map((item) => (
              <option key={item.key} value={item.key}>
                {item.label}
              </option>
            ))}
          </select>
        )}
        {filtered && (
          <button type="button" className="bnf-wq-clear" onClick={onClear}>
            Clear filters
          </button>
        )}
      </div>
    </div>
  );
}
