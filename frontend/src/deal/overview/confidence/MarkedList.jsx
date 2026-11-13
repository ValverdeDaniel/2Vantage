import { Link } from 'react-router';
import { markedMeta, rowPath } from './confidenceWords';

/**
 * One list of marked values (plan.md §8.6; M90, M91; old Vantage 891f1b3 `DataConfidence.jsx` MarkedList): the record
 * of what someone decided to leave as read (Ignored) or flagged for a second look (Needs checking), newest first —
 * where the value lives (a link to its tab), the field, the value (never for member data: the server sends none), who,
 * when and from which file — each with its buttons, then "and N more" past the first fifty.
 */
export default function MarkedList({ title, dealId, list, total, busy, actions, onAction, headAction = null }) {
  if (!list.rows.length) return null;
  return (
    <div className="bnf-ov-marked">
      <div className="bnf-ov-marked-head">
        <span className="bnf-ov-audit-title">
          {title} ({total})
        </span>
        {headAction}
      </div>
      {list.rows.map((row) => (
        <div key={row.ref} className="bnf-ov-marked-row">
          <span className="bnf-ov-marked-what">
            <Link className="bnf-override-link" title="Open where this value lives" to={rowPath(dealId, row)}>
              {row.where}
            </Link>
            {' · '}
            {row.label}
            {row.value != null && row.value !== '' && <span className="bb-mono"> · {row.value}</span>}
            {/* Under the value, not in a grid cell of its own (the old's third column): a file's name there took the
                row's width and squeezed the value to nothing (M90). */}
            <span className="bb-drop-meta" style={{ display: 'block' }}>
              {markedMeta(row)}
            </span>
          </span>
          <span className="bnf-ov-marked-actions">
            {actions.map((entry) => (
              <button
                key={entry.action}
                type="button"
                className="btn btn-secondary btn-sm"
                disabled={!!busy}
                onClick={() => onAction(row, entry.action)}
              >
                {busy === `${entry.action}:${row.ref}` ? '…' : entry.label}
              </button>
            ))}
          </span>
        </div>
      ))}
      {list.more > 0 && <div className="bb-drop-meta">and {list.more} more — newest shown first</div>}
    </div>
  );
}
