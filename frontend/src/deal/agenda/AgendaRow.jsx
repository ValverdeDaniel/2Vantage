import { Link } from 'react-router';
import { actionsOf, dayLabel, detailOf, dotOf } from './rowView';

/*
 * One Agenda row (I10–I14, I30, I35): the date (follow-ups, tasks and nudges only), the severity dot, the words and
 * their detail, the chip, "Open ▸" to where the work is done (and, beside the census step, "Census ▸"; I50), then its
 * buttons. A blocked row is muted. The form a button opens renders under the row. Markup and classes of old Vantage
 * 891f1b3 `shared/agenda/AgendaParts.jsx` AgendaRow.
 */
export default function AgendaRow({ row, meta, flash, rowRef, busy, onAction, form }) {
  const detail = detailOf(row, meta);
  return (
    <div className={`bnf-ag-item ${flash ? 'bnf-agenda-flash' : ''}`} ref={rowRef} data-row={row.id}>
      <div className={`bnf-ag-row ${row.section === 'blocked' ? 'bnf-ag-muted' : ''}`}>
        <div className="bnf-cal-date bb-mono" title={row.date ? dayLabel(row.date) : ''}>
          {row.date ? dayLabel(row.date) : ''}
        </div>
        <div className={`bnf-cal-dot bnf-dot-${dotOf(row)}`} />
        <div className="bnf-cal-main">
          <span className="bnf-cal-label">{row.label}</span>
          {detail && <span className="bnf-agenda-detail">{detail}</span>}
        </div>
        <div className="bnf-ag-actions">
          {row.chip && <span className="bnf-ag-chip bnf-ag-chip-task">{row.chip}</span>}
          {row.link && (
            <Link className="bnf-agenda-open" to={row.link} title="Open where this work is done">
              Open ▸
            </Link>
          )}
          {row.also && (
            <Link className="bnf-agenda-open" to={row.also.link}>
              {row.also.label}
            </Link>
          )}
          {actionsOf(row).map((action) => (
            <button
              key={action.key}
              type="button"
              className={action.tick ? 'bnf-cal-done' : 'bnf-ag-btn'}
              title={action.title}
              aria-label={action.tick ? action.title : undefined}
              disabled={busy}
              onClick={() => onAction(row, action.key)}
            >
              {busy && action.key === 'tick' ? '…' : action.label}
            </button>
          ))}
        </div>
      </div>
      {form}
    </div>
  );
}
