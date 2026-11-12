import { labelOf } from '../../api/meta';
import CvgCheck from './CvgCheck';

/*
 * One line of the Coverage & marketing intent card (B16–B18; old `CoverageIntentPanel.jsx`, 891f1b3): the Line cell
 * (label, state, the gap words, the unanswered question with its one-click No, the note chip), In force, Current plan
 * (the row's carrier, funding and renewal date; read-only from the Advisor's current plans once it has them, §6.5),
 * Documents, the three THIS YEAR boxes with "＋ guarantee" under Keep as-is, and ×. The note opens as a sub-row.
 */
function onBlurSave(current, save) {
  return (event) => {
    const next = event.target.value.trim();
    if (next !== (current || '')) save(next);
  };
}

function CurrentPlan({ row, meta, locked, onPatch }) {
  if (!row.answered) return <span className="bb-drop-meta">—</span>;
  if (!row.in_force) return <span className="bb-drop-meta">Not offered today</span>;
  const funding = meta?.funding || [];
  return (
    <div className="bnf-cvg-plan">
      {row.from_plans ? (
        <span className="bb-drop-meta" title="From the current plans in the Advisor — edit them there">
          {[row.from_plans.carrier, labelOf(funding, row.from_plans.funding)].filter(Boolean).join(' · ') || '—'}
        </span>
      ) : (
        <>
          <input
            key={`carrier:${row.carrier}`}
            className="bnf-intake-input"
            defaultValue={row.carrier}
            placeholder="Carrier"
            aria-label={`${row.label} carrier`}
            disabled={locked}
            onBlur={onBlurSave(row.carrier, (carrier) => onPatch({ carrier }))}
          />
          <select
            className="bnf-intake-input"
            value={row.funding || ''}
            aria-label={`${row.label} funding`}
            disabled={locked}
            onChange={(event) => onPatch({ funding: event.target.value })}
          >
            <option value="">Funding…</option>
            {funding.map((option) => (
              <option key={option.key} value={option.key}>
                {option.label}
              </option>
            ))}
          </select>
        </>
      )}
      <input
        key={`renewal:${row.renewal_date || ''}`}
        type="date"
        className="bnf-intake-input bnf-w-narrow"
        defaultValue={row.renewal_date || ''}
        title="Renewal date"
        aria-label={`${row.label} renewal date`}
        disabled={locked}
        onBlur={onBlurSave(row.renewal_date, (renewal_date) => onPatch({ renewal_date }))}
      />
    </div>
  );
}

function Guarantee({ row, open, locked, onOpen, onPatch }) {
  if (!(row.answered && row.in_force && row.this_year === 'keep')) return null;
  const title = 'Rates guaranteed through — the usual reason a line is not shopped';
  if (!row.rate_guarantee_through && !open) {
    return (
      <button type="button" className="bnf-cvg-guarbtn" title={title} disabled={locked} onClick={() => onOpen(true)}>
        ＋ guarantee
      </button>
    );
  }
  return (
    <input
      key={`guarantee:${row.rate_guarantee_through || ''}`}
      type="date"
      className="bnf-intake-input bnf-cvg-guarantee"
      autoFocus={!row.rate_guarantee_through}
      defaultValue={row.rate_guarantee_through || ''}
      title={title}
      aria-label={`${row.label} rate guarantee`}
      disabled={locked}
      onBlur={(event) => {
        const next = event.target.value || '';
        if (next !== (row.rate_guarantee_through || '')) onPatch({ rate_guarantee_through: next });
        if (!next) onOpen(false);
      }}
    />
  );
}

export default function CoverageRow({ row, meta, years, locked, busy, docs, noteOpen, onNote, guarOpen, onGuar,
  onIntent, onPatch, colSpan }) {
  const hasNote = Boolean(row.notes);
  return (
    <>
      <tr className={row.answered ? '' : 'is-unanswered'}>
        <td className="bnf-cvg-linecell">
          <div className="bnf-cvg-linehead">
            <div className="bnf-cvg-lineid">
              <div className="bnf-cvg-line">{row.label}</div>
              {row.state_label && <div className="bb-drop-meta">{row.state_label}</div>}
            </div>
          </div>
          {row.answered && !row.in_force && <div className="bb-drop-meta bnf-cvg-vocab">reads as Quote it / Present it</div>}
          {!row.answered && (
            <div className="bb-drop-meta bnf-cvg-ask">
              Do they have {row.label.toLowerCase()} today? Tick In force, or{' '}
              <button type="button" className="bnf-cvg-nolink" disabled={locked} onClick={() => onIntent({ has_today: false })}>
                No
              </button>
            </div>
          )}
          <button
            type="button"
            className={`bnf-cvg-notebtn ${hasNote ? 'has-note' : ''}`}
            aria-expanded={noteOpen}
            title={hasNote ? row.notes : 'Add a note about this line'}
            onClick={() => onNote(!noteOpen)}
          >
            {hasNote ? `📝 Note${noteOpen ? ' ▾' : ' ▸'}` : '＋ note'}
          </button>
        </td>
        <td>
          <CvgCheck
            state={row.answered && row.in_force ? 'on' : ''}
            tone={row.answered ? '' : 'is-asking'}
            disabled={locked}
            label={`${row.label} in force`}
            title={
              row.answered
                ? row.in_force
                  ? 'They have this today — click to say they do not'
                  : 'They do not have this today — click to say they do'
                : 'Nobody has said yet whether they have this today'
            }
            onClick={() => onIntent({ has_today: !(row.answered && row.in_force) })}
          />
        </td>
        <td>
          <CurrentPlan row={row} meta={meta} locked={locked} onPatch={onPatch} />
        </td>
        <td>{docs}</td>
        {years.map((column) => (
          <td key={column.key}>
            <CvgCheck
              state={row.this_year === column.key ? 'on' : ''}
              disabled={locked || !row.answered}
              label={`${row.label}: ${column.label}`}
              title={
                row.answered
                  ? row.this_year === column.key
                    ? row.this_year_label
                    : `Set this line to “${column.label}”`
                  : 'Answer In force first'
              }
              onClick={() => onIntent({ this_year: column.key })}
            />
            {column.key === 'keep' && (
              <Guarantee row={row} open={guarOpen} locked={locked} onOpen={onGuar} onPatch={onPatch} />
            )}
          </td>
        ))}
        <td>
          <button
            type="button"
            className="bnf-cvg-remove"
            title="Take this line out of the conversation"
            aria-label={`Take ${row.label} out of the conversation`}
            disabled={busy}
            onClick={() => onIntent({ remove: true })}
          >
            ×
          </button>
        </td>
      </tr>
      {noteOpen && (
        <tr className="bnf-cvg-noterow">
          <td colSpan={colSpan}>
            <label className="bnf-cvg-notelabel" htmlFor={`cvg-note-${row.line}`}>
              Note · {row.label}
            </label>
            <textarea
              id={`cvg-note-${row.line}`}
              className="bnf-intake-input bnf-cvg-note"
              rows={2}
              maxLength={300}
              autoFocus={!row.notes}
              defaultValue={row.notes || ''}
              placeholder="Anything worth remembering about this line — plan design, rates, what the client said…"
              disabled={locked}
              onBlur={(event) => {
                const next = event.target.value.trim();
                if (next !== (row.notes || '')) onPatch({ notes: next });
                if (!next) onNote(false);
              }}
            />
          </td>
        </tr>
      )}
    </>
  );
}
