import { formatDate } from '../../lib/format';

/*
 * A record's history (H57; 891f1b3 `RecordDrawer.jsx`'s history list, its classes): each Activity row that touched
 * it, newest first, with every key's before → after. The all tier's only (the server sends none to anyone else).
 */
function shown(value) {
  if (value == null || value === '') return '—';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

export default function RecordHistory({ history }) {
  return (
    <div data-guide="record-history">
      <div className="bnf-com-section-title">History</div>
      {history.length === 0 && <div className="bb-drop-meta">No changes logged.</div>}
      {history.length > 0 && (
        <ul className="bnf-com-history">
          {history.map((row) => (
            <li key={row.id}>
              {row.summary}
              <span className="bb-drop-meta">
                {' '}
                · {row.actor} · {formatDate(row.at)}
              </span>
              {Object.entries(row.changes || {})
                .filter(([key]) => key !== 'terms')
                .map(([key, [before, after]]) => (
                  <div key={key} className="bb-drop-meta">
                    <code>{key}</code> {shown(before)} → {shown(after)}
                  </div>
                ))}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
