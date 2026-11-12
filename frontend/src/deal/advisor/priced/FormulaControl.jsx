import { useState } from 'react';

/*
 * One rate's change (plan.md §8.14; F77; the old FormulaControl): the operation and its amount. While an all-rates
 * change is set, the empty choice reads as what it inherits ("as all (% off 5)") and "unchanged" leaves this rate out
 * of it (`keep`). `item` is {op, value}, `keep`, or nothing; `onChange` gets the same, or null for "as all".
 */
export default function FormulaControl({ item, onChange, inherit, ops, keep, disabled }) {
  const [focusValue, setFocusValue] = useState(false);
  const op = item === keep ? keep : item?.op || '';
  const choices = inherit
    ? [{ key: '', label: inherit }, { key: keep, label: 'unchanged' }, ...ops]
    : [{ key: '', label: 'unchanged' }, ...ops];
  return (
    <span className="bnf-pv-formula">
      <select
        className="bnf-pv-formula-op"
        value={op}
        disabled={disabled}
        aria-label="Change"
        onChange={(event) => {
          const next = event.target.value;
          setFocusValue(Boolean(next) && next !== keep);
          if (!next) onChange(null);
          else if (next === keep) onChange(keep);
          else onChange({ op: next, value: item?.value ?? '' });
        }}
      >
        {choices.map((choice) => (
          <option key={choice.key || 'inherit'} value={choice.key}>
            {choice.label}
          </option>
        ))}
      </select>
      {op && op !== keep && (
        <input
          type="number"
          className="bnf-pv-formula-val"
          step="0.25"
          min="0"
          aria-label="Amount"
          value={item?.value ?? ''}
          autoFocus={focusValue}
          disabled={disabled}
          onChange={(event) => onChange({ op, value: event.target.value })}
        />
      )}
    </span>
  );
}
