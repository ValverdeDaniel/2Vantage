import { formatDate } from '../lib/format';
import cx from '../ui/cx';

/*
 * One value in the List (plan.md §8.16; E56, D122; the old FileReviewList row): its bucket's word in its tone, the
 * field and the plan it is on (never a person: plan values only), the value as the member reads it, where it is in the
 * file (p. 2, Medical B11) and a person's mark. `file` names the file under 📚 All proposals.
 */

const by = (stamp) =>
  [stamp?.by_name ? `by ${stamp.by_name}` : '', stamp?.at ? `on ${formatDate(stamp.at)}` : ''].filter(Boolean).join(' ');

function MarkChip({ row }) {
  if (row.confirmed && !row.mark) {
    return (
      <span className="bnf-frl-mark bnf-frl-mark-ok" title={`Approved ${by(row.confirmed)}`.trim()}>
        ✓ Approved
      </span>
    );
  }
  if (row.mark?.state === 'ignored') {
    return (
      <span className="bnf-frl-mark" title={`Warning ignored ${by(row.mark)} — the value stays as read`.trim()}>
        Ignored
      </span>
    );
  }
  if (row.mark?.state === 'check') {
    return (
      <span className="bnf-frl-mark bnf-frl-mark-check" title={`Needs checking — flagged ${by(row.mark)}`.trim()}>
        ⚑ Needs checking
      </span>
    );
  }
  return null;
}

export default function ReviewListRow({ row, bucket, value, file, selected, open, onClick, onDoubleClick }) {
  return (
    <div
      id={`frl-${row.ref}`}
      role="option"
      aria-selected={selected}
      className={cx('bnf-frl-row', selected && 'is-active', open && 'is-open', row.dealt && 'is-dealt')}
      data-ref={row.ref}
      onClick={onClick}
      onDoubleClick={onDoubleClick}
      title={open ? 'Open in the file' : 'Press F (or double-click) to see it in the file'}
    >
      <span className={`bnf-frl-state bnf-frl-tone-${bucket?.tone ?? 'grey'}`} title={bucket?.help}>
        {bucket?.label ?? row.bucket}
      </span>
      <span className="bnf-frl-label">
        {row.label}
        {row.sub && <span className="bnf-frl-sub">{row.sub}</span>}
        {file && <span className="bnf-frl-sub bnf-frl-file">📄 {file}</span>}
      </span>
      <span className="bnf-frl-value">{value || '—'}</span>
      <span className="bnf-frl-where">{row.where}</span>
      <MarkChip row={row} />
    </div>
  );
}
