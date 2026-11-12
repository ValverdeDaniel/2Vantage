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
