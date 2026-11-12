// How a stored value reads on screen (plan.md §3.9): amounts $3,300, percent 20%, rates $512.34, choices by label.
// Display only, shared by the Advisor's board and the Documents station's List; every figure comes from the server.
import { formatMoney, formatRate } from './format';

const NUMBER = /^-?\d+(\.\d+)?$/;

/** A stored value as the member reads it, from its field's meta entry ({type, choices}); '' when blank. */
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
