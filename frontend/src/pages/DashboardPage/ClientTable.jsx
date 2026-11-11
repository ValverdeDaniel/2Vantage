import { Link, useNavigate } from 'react-router';
import { LOST, relationshipLabel, SOLD, stageLabel } from '../../api/meta';
import { formatDate, formatDateTime, formatUpdated, personName } from '../../lib/format';
import Badge from '../../ui/Badge';
import VisuallyHidden from '../../ui/VisuallyHidden';
import styles from './ClientTable.module.css';

// The API sorts two ways only: Client A→Z (ordering=name) and Last updated newest first (-last_activity).
function SortHeader({ label, active, direction, onSort }) {
  return (
    <th scope="col" aria-sort={active ? direction : 'none'}>
      <button type="button" className={styles.sort} onClick={onSort}>
        {label}
        <span aria-hidden="true" className={active ? styles.sortOn : styles.sortOff}>
          {active ? (direction === 'ascending' ? '▲' : '▼') : '↕'}
        </span>
        {!active && <VisuallyHidden>, sort by {label.toLowerCase()}</VisuallyHidden>}
      </button>
    </th>
  );
}

function StageBadge({ stage, meta }) {
  if (stage === LOST) return <Badge tone="muted">{stageLabel(meta, stage)}</Badge>;
  if (stage === SOLD) {
    return (
      <Badge tone="success" icon="✓">
        {stageLabel(meta, stage)}
      </Badge>
    );
  }
  return <Badge tone="brand">{stageLabel(meta, stage)}</Badge>;
}

/** Dashboard rows (plan.md §7.3 client row). A row opens /deals/<deal id>; the name is the keyboard link. */
export default function ClientTable({ rows, meta, ordering, onSort }) {
  const navigate = useNavigate();
  return (
    <div className={styles.wrap}>
      <table className={styles.table}>
        <thead>
          <tr>
            <SortHeader label="Client" active={ordering === 'name'} direction="ascending" onSort={() => onSort('name')} />
            <th scope="col">Type</th>
            <th scope="col">Stage</th>
            <th scope="col">Effective</th>
            <th scope="col">Owner</th>
            <SortHeader
              label="Last updated"
              active={ordering === '-last_activity'}
              direction="descending"
              onSort={() => onSort('-last_activity')}
            />
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const href = `/deals/${row.deal.id}`;
            const lost = row.deal.stage === LOST;
            return (
              <tr
                key={row.id}
                className={lost ? `${styles.row} ${styles.lost}` : styles.row}
                onClick={(event) => {
                  if (!event.target.closest('a, button')) navigate(href);
                }}
              >
                <td>
                  <Link to={href} className={styles.name}>
                    {row.name}
                  </Link>
                </td>
                <td>{relationshipLabel(meta, row.relationship)}</td>
                <td>
                  <StageBadge stage={row.deal.stage} meta={meta} />
                </td>
                <td>{formatDate(row.deal.effective_date, '—')}</td>
                <td>{personName(row.owner, '—')}</td>
                <td>
                  <time dateTime={row.last_activity_at} title={formatDateTime(row.last_activity_at)}>
                    {formatUpdated(row.last_activity_at)}
                  </time>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
