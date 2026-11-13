import { Link, useNavigate } from 'react-router';
import { stageLabel } from '../../api/meta';
import { initialsOf, stagePillClass } from '../../lib/dealLook';
import { formatDate } from '../../lib/format';
import { ACTION_ICONS, agoWords, barClass } from './homeRows';

// Cells the Prospects and Work queue tables share (old HomeCells.jsx at 891f1b3; I76, I77, L118), over the work
// feed's rows. Two targets per row, so the reader chooses: the NAME opens the deal (`home`), the chip does the next
// action (`link`); the row's background keeps the action, as it always did.

/** A header cell that sorts (old SortTh): a div, as the old one was, with Enter and Space too. */
export function SortTh({ className, sortKey, sort, onSort, title, children }) {
  const caret = sort?.key === sortKey ? (sort.dir === 'asc' ? ' ▲' : ' ▼') : '';
  return (
    <div
      role="button"
      tabIndex={0}
      className={`${className} bnf-th-sortable`}
      title={title}
      onClick={() => onSort(sortKey)}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          onSort(sortKey);
        }
      }}
    >
      {children}
      {caret}
    </div>
  );
}

/** The avatar, the client's name as the link that opens the deal, and the row's sub-line. */
export function RowAccountCell({ row, sub }) {
  return (
    <div className="bb-th-account bb-account-cell">
      <div className="bb-avatar" aria-hidden="true">
        {initialsOf(row.client_name)}
      </div>
      <div>
        <Link
          to={row.home}
          className="bb-account-name bnf-wq-namebtn"
          title="Open this deal — see everything on it"
          onClick={(event) => event.stopPropagation()}
        >
          {row.client_name}
        </Link>
        <div className="bb-account-sub">{sub}</div>
      </div>
    </div>
  );
}

/** The next action's chip (I76): its severity's icon and colour, opening the step's tab. */
export function ActionCell({ row }) {
  const navigate = useNavigate();
  if (!row) return <div className="bnf-th-action" />;
  return (
    <div className="bnf-th-action">
      <button
        type="button"
        className={`bnf-action-chip bnf-action-btn bnf-action-${row.severity}`}
        title="Go to this action"
        onClick={(event) => {
          event.stopPropagation();
          navigate(row.link);
        }}
      >
        {ACTION_ICONS[row.severity]} {row.label}
      </button>
    </div>
  );
}

export const RESPONSE_TITLE =
  'What the client sent on their link — questions and answers to our forms — and whether we have answered it. ' +
  'Sorts by when they last reached out.';

const REACHED = { asked: 'asked a question', answered: 'answered', submitted: 'submitted', uploaded: 'sent a file' };
const plural = (n, one) => `${n} ${one}${n === 1 ? '' : 's'}`;

function responseTitle(found) {
  const lines = [];
  if (found.questions) lines.push(`${plural(found.questions, 'question')} from the client waiting on our answer`);
  if (found.answers) lines.push(`${plural(found.answers, 'answer')} from the client to review`);
  if (found.answering) lines.push(`${plural(found.answering, 'answer')} still being typed`);
  if (!lines.length) lines.push('Everything they sent has been answered or reviewed');
  lines.push('Click to open the deal’s Review & requests');
  return lines.join('\n');
}

/** The Client response column (L118; old D-159): what the client sent and whether we handled it; opens Review. */
export function ResponseCell({ row }) {
  const navigate = useNavigate();
  const found = row.response;
  if (!found) return <div className="bnf-th-response bb-account-sub">—</div>;
  const chips = [];
  if (found.questions) chips.push(['question', `? ${found.questions} unanswered`]);
  if (found.answers) chips.push(['answers', `↩ ${found.answers} to review`]);
  if (!chips.length) {
    chips.push(found.state === 'answering' ? ['answering', '✎ Still answering'] : ['handled', '✓ Handled']);
  }
  const open = (event) => {
    event.stopPropagation();
    navigate(row.review_link);
  };
  return (
    <div className="bnf-th-response" title={responseTitle(found)}>
      <div className="bnf-response-chips">
        {chips.map(([tone, words]) => (
          <button key={tone} type="button" className={`bnf-response-chip bnf-response-${tone}`} onClick={open}>
            {words}
          </button>
        ))}
      </div>
      <div className="bnf-response-when">
        {found.who ? `${found.who} · ` : ''}
        {REACHED[found.kind] || 'answered'} {agoWords(found.at)}
      </div>
    </div>
  );
}

/** A deal's stage pill and progress bar; one of its steps, the pill alone; a task's or nudge's category chip. */
export function StageCell({ row, meta }) {
  const pill = <span className={stagePillClass(row.stage)}>{stageLabel(meta, row.stage)}</span>;
  if (row.kind === 'step') return <div className="bnf-wq-th-extra">{pill}</div>;
  if (row.kind !== 'deal') {
    const label = (meta.agenda?.queue?.categories || []).find((item) => item.key === row.category)?.label;
    return (
      <div className="bnf-wq-th-extra">
        <span className={`bnf-cat-chip bnf-cat-${row.category} bnf-cat-static`}>{label}</span>
      </div>
    );
  }
  return (
    <div className="bnf-wq-th-extra">
      <div className="bnf-wq-stagecell">
        {pill}
        <div className="bb-bar-track bnf-wq-bar">
          <div
            className={`bb-bar-fill ${barClass(row.progress_pct ?? 0)}`}
            style={{ width: `${row.progress_pct ?? 0}%` }}
          />
        </div>
      </div>
    </div>
  );
}

/** Due: the effective date (a step's or task's own day), red once past (`due_in` from the agency's today). */
export function DueCell({ row }) {
  const overdue = row.due_in !== null && row.due_in !== undefined && row.due_in < 0;
  return (
    <div className={overdue ? 'bb-th-date bb-mono bnf-wq-overdue' : 'bb-th-date bb-mono'}>
      {formatDate(row.due, '—')}
    </div>
  );
}

export function OwnerCell({ row }) {
  return <div className="bnf-th-owner bb-account-sub">{row.owner_name || '—'}</div>;
}
