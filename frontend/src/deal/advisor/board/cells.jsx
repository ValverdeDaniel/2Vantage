import { formatMoney, formatPercent } from '../../../lib/format';
import cx from '../../../ui/cx';
import { displayValue, enrollmentText, SOURCE_WORDS } from '../display';
import { networkType } from './boardModel';

/*
 * The board's small cells (plan.md §8.14; F41, F50, F57; the old AdvisorTab's derived columns): the ★, the ☐ tick
 * and the header's select-all box, the derived figures (Monthly total, Δ vs current, Network / type, Flags) and a
 * plan value as the member reads it. Every figure is the server's; these only word it.
 */

export function StarButton({ plan, busy, onToggle }) {
  if (plan.role === 'current') return null; // the baseline is always on the proposal and takes no star
  return (
    <button
      type="button"
      className={cx('bnf-star-btn', plan.starred && 'active')}
      aria-pressed={plan.starred}
      aria-label={`${plan.starred ? 'Unstar' : 'Star'} ${plan.carrier} — ${plan.name}`}
      title={plan.starred ? 'Remove from shortlist' : 'Add to shortlist'}
      disabled={busy}
      onClick={() => onToggle(plan)}
    >
      {plan.starred ? '★' : '☆'}
    </button>
  );
}

export function TickBox({ plan, checked, blocked, hint, onToggle }) {
  return (
    <input
      type="checkbox"
      className="bnf-move-check"
      aria-label={`Select ${plan.carrier} — ${plan.name}`}
      title={blocked || hint}
      disabled={Boolean(blocked)}
      checked={!blocked && checked}
      onChange={() => onToggle(plan.id)}
    />
  );
}

/** The header's box: every quote the board is showing, never the pinned current plans (F57). */
export function SelectAllBox({ ids, ticked, editing, onChange }) {
  const all = ids.length > 0 && ids.every((id) => ticked.has(id));
  const some = ids.some((id) => ticked.has(id));
  const title = ids.length
    ? `Select the ${ids.length} plan${ids.length === 1 ? '' : 's'} the board is showing, to star them` +
      (editing ? ', move them or mark them current' : '')
    : 'No plan is showing';
  return (
    <input
      type="checkbox"
      className="bnf-move-check"
      aria-label="Select every plan shown"
      title={title}
      disabled={!ids.length}
      checked={all}
      ref={(el) => {
        if (el) el.indeterminate = some && !all;
      }}
      onChange={() => onChange(ids, !all)}
    />
  );
}

function Total({ plan }) {
  const monthly = plan.premium?.monthly;
  if (monthly == null) {
    return <span title={plan.premium?.reason_words || undefined}>—</span>;
  }
  const source = plan.enrollment_source;
  return (
    <>
      {formatMoney(monthly)}
      {source && SOURCE_WORDS[source] && (
        <span
          className="bnf-pc-mark"
          title={`Priced on counts typed ${SOURCE_WORDS[source] === 'typed' ? 'for this plan' : `(${SOURCE_WORDS[source]})`}: ${enrollmentText(plan.enrollment_used, Object.keys(plan.enrollment_used ?? {}))}`}
        >
          ✎ counts
        </span>
      )}
    </>
  );
}

function Delta({ plan }) {
  if (plan.role === 'current') return <span className="bnf-delta-base">baseline</span>;
  const pct = plan.change?.pct;
  if (pct == null) {
    const title = plan.part_of ? `Part of ${plan.part_of}'s enrollment — see the packages` : undefined;
    return <span title={title}>—</span>;
  }
  return <span className={cx('bnf-delta', pct > 0 ? 'bnf-delta-pos' : 'bnf-delta-neg')}>{formatPercent(pct)}</span>;
}

function Flags({ plan }) {
  const flags = plan.facts?.flags ?? 0;
  return (
    <span className="bnf-flag-cell">
      {flags > 0 && (
        <span className="bnf-flag-chip" title="Values the reader was unsure of, or that someone flagged">
          ⚠ {flags} to review
        </span>
      )}
      {flags === 0 && plan.facts?.incomplete && <span className="bnf-flag-chip">incomplete</span>}
    </span>
  );
}

/** A derived column's cell (F41). */
export function DerivedValue({ col, plan }) {
  switch (col.key) {
    case 'total':
      return <Total plan={plan} />;
    case 'delta':
      return <Delta plan={plan} />;
    case 'network_type':
      return networkType(plan) || '—';
    case 'flags':
      return <Flags plan={plan} />;
    default:
      return null;
  }
}

/** A plan value as the member reads it ($3,300; 20%; $512.34), or — when blank. */
export function FieldValue({ col, plan }) {
  return displayValue(col.field, plan.values?.[col.key]) || '—';
}
