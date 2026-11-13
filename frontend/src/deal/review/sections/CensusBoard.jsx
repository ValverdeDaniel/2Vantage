import { useState } from 'react';
import { useSetRules } from '../../../api/reviewForm';
import { useTrayAsk } from '../../../api/reviewTray';
import { errorText } from '../../../lib/errors';
import { useToast } from '../../../ui/useToast';
import cx from '../../../ui/cx';
import { activeCount, censusColumns, EMPTY_CENSUS, groupsOf, toggled } from './boardModel';
import { BoardFilters } from './BoardFilters';
import CensusColumnRow from './CensusColumnRow';
import CensusLens from './CensusLens';

const SCOPES = [
  { key: 'missing', label: 'Just what is missing' },
  { key: 'blank', label: 'Every blank' },
];

/*
 * The Census board (plan.md §8.8; C27, C28, C30, L46, L47; old 891f1b3 `CensusReviewView.jsx`): By field — a row per
 * column, with filters (band, status, origin, search, required only, hide complete, only quoted, hide waived), ticks
 * that ask the client for the picked columns' blanks ("＋ Ask N", just what is missing or every blank, into the request
 * tray) and Auto · Required · Waived per column (OQ17) — or By person (C30), the lens that lists each person's blanks to
 * pick cell by cell. Past 400 blanks it recommends asking for their census file. Saved filter setups wait (OQ7).
 */
export default function CensusBoard({ dealId, board, meta, readOnly }) {
  const [lens, setLens] = useState('field');
  const [filters, setFilters] = useState(EMPTY_CENSUS);
  const [picked, setPicked] = useState([]);
  const [scope, setScope] = useState('missing');
  const [open, setOpen] = useState('');
  const rules = useSetRules(dealId);
  const ask = useTrayAsk(dealId);
  const toast = useToast();
  const columns = censusColumns(board.columns, filters);
  const origins = {};
  board.columns.forEach((column) => Object.entries(column.origins).forEach(([key, n]) => (origins[key] = (origins[key] || 0) + n)));
  const run = (promise, words) => promise.then((answer) => toast.success(words(answer))).catch((error) => toast.error(errorText(error)));
  const setRule = (column, rule) =>
    run(rules.mutateAsync({ surface: 'census', rules: { [column.key]: rule } }), () => `${column.label}: ${rule} on this deal`);
  const askColumns = () =>
    run(ask.mutateAsync({ census: { columns: picked, scope } }), (answer) => {
      setPicked([]);
      return `${answer.added} added to the request tray`;
    });
  return (
    <div className="bnf-board-section-board">
      <div className="bnf-census-lanehead">
        <div className="bb-tab-title">Missing</div>
        {!readOnly && (
          <button type="button" className="btn btn-secondary btn-sm" disabled={ask.isPending}
            onClick={() => run(ask.mutateAsync({ refs: ['census:file'], skip_out: true }), (answer) => (answer.added ? 'Their census file is in the request tray' : 'Already asked or in the tray'))}>
            ＋ Ask for their census file
          </button>
        )}
      </div>
      <div className="bb-subtitle bb-mb-lg">
        What this deal still needs and nobody has filled: the required gaps by column, and where every value came from. Tick
        the gaps and ask the client.
      </div>
      <div className="bnf-advisor-views" role="group" aria-label="Lens">
        <span className="bnf-advisor-views-label">Look at it</span>
        {[['field', 'By field'], ['person', 'By person']].map(([key, words]) => (
          <button key={key} type="button" className={cx('bnf-viewtab', lens === key && 'bnf-viewtab-on')} aria-pressed={lens === key} onClick={() => setLens(key)}>
            {words}
          </button>
        ))}
        <span className="bnf-review-note">
          {board.employees} employees · {board.dependents} dependents
        </span>
      </div>
      {board.file_hint && (
        <div className="bb-banner">
          {board.people.total} blanks is more than a link should ask one by one: ask for their census file instead.
        </div>
      )}
      {lens === 'person' ? (
        <CensusLens dealId={dealId} lens={board.people} readOnly={readOnly} />
      ) : (
        <>
          <BoardFilters
            filters={filters}
            active={activeCount(filters, EMPTY_CENSUS)}
            onChange={(change) => setFilters((now) => ({ ...now, ...change }))}
            onClear={() => setFilters(EMPTY_CENSUS)}
            groups={[{ key: '', label: 'All' }, ...groupsOf(board.columns, meta?.census_groups)]}
            groupKey="group"
            statuses={meta?.census_segments}
            origins={(meta?.origins || []).filter((origin) => origins[origin.key])}
            originCounts={origins}
            checks={[
              ['requiredOnly', 'Required only'],
              ['hideComplete', 'Hide complete'],
              ['quotedOnly', 'Only quoted lines'],
              ['hideWaived', 'Hide waived'],
            ]}
            searchWords="Find a column…"
          />
          <div className="bnf-review-boardhead">
            <div className="bnf-review-count">
              Showing {columns.length} of {board.columns.length} columns{picked.length > 0 && <> · <b>{picked.length}</b> selected</>}
            </div>
            {picked.length > 0 && !readOnly && (
              <div className="bnf-review-actions">
                <select value={scope} aria-label="What to ask" onChange={(event) => setScope(event.target.value)}>
                  {SCOPES.map((option) => (
                    <option key={option.key} value={option.key}>
                      {option.label}
                    </option>
                  ))}
                </select>
                <button type="button" className="btn btn-secondary btn-sm" onClick={() => setPicked([])}>
                  Clear
                </button>
                <button type="button" className="btn btn-violet btn-sm" disabled={ask.isPending} onClick={askColumns}
                  title="Ask for the picked columns' blanks: they wait in the request tray until you send them">
                  ＋ Ask {picked.length} column{picked.length === 1 ? '' : 's'}
                </button>
              </div>
            )}
          </div>
          <div className="bb-grid-card bnf-review-scroll">
            {columns.map((column) => (
              <CensusColumnRow key={column.key} dealId={dealId} column={column} meta={meta} readOnly={readOnly}
                picked={picked.includes(column.key)} expanded={open === column.key} busy={rules.isPending}
                onPick={() => setPicked((now) => toggled(now, column.key))} onRule={setRule}
                onDrill={() => setOpen(open === column.key ? '' : column.key)} />
            ))}
            {!columns.length && <div className="bnf-review-empty">No columns match these filters.</div>}
          </div>
        </>
      )}
    </div>
  );
}
