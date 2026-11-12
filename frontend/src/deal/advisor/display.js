// How Advisor values and figures read on screen. Display only — every figure comes from the server (§3.9).
import { formatMoney, formatPercent, formatRate } from '../../lib/format';

const NUMBER = /^-?\d+(\.\d+)?$/;

/** A stored value as the member reads it: amounts $3,300, percent 20%, rates $512.34, choices by label. */
export function displayValue(field, raw) {
  if (raw === undefined || raw === null || raw === '') return '';
  const numeric = NUMBER.test(String(raw));
  switch (field?.type) {
    case 'amount':
      return numeric ? formatMoney(raw) : raw;
    case 'percent':
      return numeric ? `${raw}%` : raw;
    case 'rate':
      return numeric ? formatRate(raw) : raw;
    case 'rate4':
      return numeric ? `$${raw}` : raw;
    case 'choice':
      return field.choices?.find((choice) => choice.key === raw)?.label ?? raw;
    default:
      return String(raw);
  }
}

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

export const SOURCE_WORDS = { typed: 'typed', 'from current plan': 'from current', 'from replaced plan': 'from replaced' };

export function enrollmentKeys(rateBasis) {
  if (rateBasis === 'composite') return ['EE', 'ES', 'EC', 'FAM'];
  return rateBasis === 'pepm' || rateBasis === 'stop_loss' ? ['lives'] : ['volume'];
}

