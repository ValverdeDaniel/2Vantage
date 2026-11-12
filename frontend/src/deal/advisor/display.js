// How Advisor values and figures read on screen. Display only — every figure comes from the server (§3.9).
import { formatMoney, formatPercent } from '../../lib/format';

// A stored value as the member reads it; shared with the Documents station's List since slice 17.
export { displayValue } from '../../lib/fieldValue';

/** '+$17,808 (+8.6%)' */
export function changeText(change) {
  if (!change) return '';
  const pct = change.pct === null || change.pct === undefined ? '' : ` (${formatPercent(change.pct)})`;
  return `${formatMoney(change.delta, { signed: true })}${pct}`;
}

/** '10·3·2·5' for tiers; '1,250,000' for a volume; '42' for lives. */
export function enrollmentText(enrollment, keys) {
  if (!enrollment) return '';
  if (keys.length === 1) return Number(enrollment[keys[0]] ?? 0).toLocaleString('en-US');
  return keys.map((key) => enrollment[key] ?? 0).join('·');
}

export const SOURCE_WORDS = {
  typed: 'typed',
  'from current plan': 'from current',
  'from replaced plan': 'from replaced',
  'from original plan': 'for the plan it was priced from', // a priced version prices its original's people (F87)
};

export function enrollmentKeys(rateBasis) {
  if (rateBasis === 'composite') return ['EE', 'ES', 'EC', 'FAM'];
  return rateBasis === 'pepm' || rateBasis === 'stop_loss' ? ['lives'] : ['volume'];
}

