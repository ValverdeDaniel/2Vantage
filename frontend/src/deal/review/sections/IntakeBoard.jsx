import { useState } from 'react';
import { useNavigate } from 'react-router';
import { useSetRules } from '../../../api/reviewForm';
import { useTrayAsk } from '../../../api/reviewTray';
import { errorText } from '../../../lib/errors';
import { useToast } from '../../../ui/useToast';
import { labelIn } from '../reviewModel';
import { activeCount, EMPTY_INTAKE, intakeRows, intakeSections, neededGaps, originTotals, toggled } from './boardModel';
import { BoardFilters, OriginDot } from './BoardFilters';
import RuleNote from './RuleNote';

const SEEDS = { qb: 'needed to quote', cond: 'needed when it applies', opt: 'not needed to quote' };

/*
 * The Intake board (plan.md §8.8; B37, L48, L122; old 891f1b3 `IntakeReviewView.jsx`): a row per question — the answer
 * and where it came from, whether THIS deal needs it (Auto, Required or Waived: what readiness, the `required` ask and
 * the star read), the note the client reads instead of our help text, and which open links ask it. It opens on Missing
 * (the questions required to market and the checklist's files not on file, all ticked, so "＋ Ask N" puts them in the
 * request tray at once); "All questions" is every question with its filters. "Edit on the form ▸" opens the Intake tab.
 * Read-first, never read-only: a past year still takes rules; only asking is off (L129).
 */
const missingRefs = (board, readOnly) =>
  readOnly ? [] : [...neededGaps(board.rows), ...board.documents.filter((doc) => doc.missing && !doc.draft_id && !doc.asked_at).map((doc) => doc.ref)];

export default function IntakeBoard({ dealId, board, meta, readOnly }) {
  const [filters, setFilters] = useState(EMPTY_INTAKE);
  const [all, setAll] = useState(false);
  const [picked, setPicked] = useState(() => new Set(missingRefs(board, readOnly)));
  const rules = useSetRules(dealId);
  const ask = useTrayAsk(dealId);
  const toast = useToast();
  const navigate = useNavigate();
  const rows = all ? intakeRows(board.rows, filters) : board.rows.filter((row) => row.shown && row.status === 'gap');
  const origins = originTotals(board.rows);
  const pick = (ref) => setPicked((now) => new Set(toggled([...now], ref)));
  const write = (key, change) =>
    rules
      .mutateAsync({ surface: 'intake', rules: { [key]: change } })
      .then((answer) => answer.activity_id && toast.success('Saved: readiness follows this rule now'))
      .catch((error) => toast.error(errorText(error)));
  const askPicked = () =>
    ask
      .mutateAsync({ refs: [...picked], skip_out: true })
      .then((answer) => {
        toast.success(`${answer.added} added to the request tray`);
        setPicked(new Set());
      })
      .catch((error) => toast.error(errorText(error)));
  const { counts } = board;
  return (
    <div className="bnf-board-section-board">
      <div className="bnf-census-lanehead">
        <div className="bb-tab-title">{all ? 'All questions' : 'Missing'}</div>
        <button type="button" className="btn btn-secondary btn-sm" onClick={() => {
          setAll(!all);
          setPicked(new Set(all ? missingRefs(board, readOnly) : []));
        }}>
          {all ? 'Missing' : 'All questions'}
        </button>
      </div>
      <div className="bb-subtitle bb-mb-lg">
        {all
          ? 'Every question: its answer and where it came from, whether this deal needs it, and the note the client reads.'
          : 'What this deal needs to market and nobody has filled: the questions required and the checklist documents not on file, ticked. ＋ Ask puts them in the request tray; All questions shows every question and where its answer came from.'}
      </div>
      {all && (
      <BoardFilters
        filters={filters}
        active={activeCount(filters, EMPTY_INTAKE)}
        onChange={(change) => setFilters((now) => ({ ...now, ...change }))}
        onClear={() => setFilters(EMPTY_INTAKE)}
        groups={[{ key: '', label: 'All' }, ...intakeSections(board.rows)]}
        groupKey="section"
        statuses={meta?.board_statuses}
        origins={(meta?.origins || []).filter((origin) => origins[origin.key] || filters.origins.includes(origin.key))}
        originCounts={origins}
        checks={[
          ['neededOnly', 'Needed on this deal only'],
          ['hideAnswered', 'Hide answered'],
        ]}
        searchWords="Find a question…"
      />
      )}
      <div className="bnf-review-boardhead bnf-ireview-head">
        <div>
          <div className="bnf-review-count">
            <b>{counts.gap}</b> needed gap{counts.gap === 1 ? '' : 's'} · {counts.pending} from the client awaiting
            approval · {counts.answered} answered{picked.size > 0 && <> · <b>{picked.size}</b> selected</>}
          </div>
          <div className="bnf-review-note">
            {all ? `Showing ${rows.length} of ${counts.total} questions` : `${rows.length} question${rows.length === 1 ? '' : 's'} required to market · ${board.documents.filter((doc) => doc.missing).length} checklist documents not on file`}
          </div>
        </div>
        <div className="bnf-review-actions">
          {readOnly && <span className="bnf-review-note">Editable, but no new client links</span>}
          <button type="button" className="btn btn-secondary btn-sm" disabled={readOnly || !neededGaps(rows).length}
            onClick={() => setPicked(new Set(neededGaps(rows)))}>
            Select needed gaps
          </button>
          {picked.size > 0 && (
            <>
              <button type="button" className="btn btn-secondary btn-sm" onClick={() => setPicked(new Set())}>
                Clear
              </button>
              <button type="button" className="btn btn-violet btn-sm" disabled={readOnly || ask.isPending} onClick={askPicked}
                title="Add the ticked questions to the request tray: they go with everything else you ask for, on one link">
                ＋ Ask {picked.size}
              </button>
            </>
          )}
          <button type="button" className="btn btn-secondary btn-sm" onClick={() => navigate(`/deals/${dealId}/intake`)}>
            Edit on the form ▸
          </button>
        </div>
      </div>
      <div className="bb-grid-card">
        <div className="bnf-ireview-scroll">
          <table className="bnf-ireview-table">
            <thead>
              <tr>
                <th aria-label="Select" />
                <th>Question</th>
                <th>Answer · where it came from</th>
                <th>Needed on this deal?</th>
                <th>Note to the client</th>
                <th>Asked in</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.key} className={`${row.shown ? '' : 'bnf-ireview-hidden'}${row.status === 'gap' ? ' bnf-ireview-gap' : ''}`}>
                  <td>
                    {row.draft_id ? (
                      <span className="bnf-in-tray" title="Waiting in the request tray">✓ In tray</span>
                    ) : (
                      <input type="checkbox" checked={picked.has(row.ref)} disabled={readOnly || !row.shown}
                        aria-label={`Ask for ${row.label}`} title={row.shown ? '' : 'Not on the form while its condition is unmet'}
                        onChange={() => pick(row.ref)} />
                    )}
                  </td>
                  <td>
                    <div className="bnf-ireview-label">
                      {row.label}
                      {row.needed && <span className="bnf-qb-star" title="Needed on this deal">*</span>}
                    </div>
                    <div className="bnf-review-note">{row.section_label}</div>
                  </td>
                  <td>
                    {row.value ? <div className="bnf-ireview-value">{row.value}</div> : <div className="bb-muted">{row.status === 'gap' ? 'Needed — blank' : 'Blank'}</div>}
                    {row.origin && (
                      <span className="rr-origin-chip" title={labelIn(meta?.origins, row.origin)}>
                        <OriginDot origin={(meta?.origins || []).find((o) => o.key === row.origin)} /> {labelIn(meta?.origins, row.origin)}
                      </span>
                    )}
                    {row.status === 'pending' && <div className="rr-differs-chip">{row.differs ? 'The client sent something different' : 'From the client, waiting'}: {row.theirs}</div>}
                  </td>
                  <td>
                    <div className="bnf-review-reqtoggle bnf-ireview-req">
                      {(meta?.intake_rules || []).map((choice) => (
                        <button key={choice.key || 'auto'} type="button" disabled={rules.isPending}
                          className={`bnf-review-reqbtn${choice.key === 'waived' ? ' bnf-review-reqbtn-waived' : ''}${row.rule === choice.key ? ' bnf-review-reqbtn-on' : ''}`}
                          title={choice.key ? '' : `By default: ${SEEDS[row.seed]}`}
                          onClick={() => row.rule !== choice.key && write(row.key, { state: choice.key })}>
                          {choice.label}
                        </button>
                      ))}
                    </div>
                    <div className="bnf-review-note">
                      {row.needed ? 'Needed here' : 'Not needed here'}
                      {!row.rule && ` · ${SEEDS[row.seed]}`}
                    </div>
                  </td>
                  <td>
                    <RuleNote note={row.note} limit={meta?.note_rule_limit} busy={rules.isPending} onSave={(note) => write(row.key, { note })} />
                  </td>
                  <td>
                    {row.asked_in.length ? row.asked_in.map((who) => <span key={who} className="bnf-ireview-asked">{who}</span>) : <span className="bb-muted">—</span>}
                  </td>
                </tr>
              ))}
              {!rows.length && (
                <tr>
                  <td colSpan={6} className="bnf-review-empty">
                    {all ? 'No questions match these filters.' : 'No question this deal needs to market is blank.'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
      {!all && <MissingDocuments documents={board.documents.filter((doc) => doc.missing)} picked={picked} onPick={pick} readOnly={readOnly} />}
    </div>
  );
}

function MissingDocuments({ documents, picked, onPick, readOnly }) {
  if (!documents.length) return null;
  return (
    <div className="bb-grid-card bnf-ireview-docs">
      <div className="bnf-ireview-docs-head">
        <span className="bb-panel-title">Checklist documents not on file</span>
        <span className="bnf-review-note">The client uploads these on their link.</span>
      </div>
      {documents.map((doc) => (
        <label key={doc.ref} className="bnf-ireview-doc">
          {doc.draft_id ? (
            <span className="bnf-in-tray" title="Waiting in the request tray">✓ In tray</span>
          ) : (
            <input type="checkbox" checked={picked.has(doc.ref)} disabled={readOnly} onChange={() => onPick(doc.ref)} />
          )}
          <span className="bnf-ireview-doc-text">
            <span className="bnf-ireview-label">{doc.label}</span>
            {doc.asked_at && <span className="bnf-review-note">Asked</span>}
          </span>
        </label>
      ))}
    </div>
  );
}
