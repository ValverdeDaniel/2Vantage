import { useState } from 'react';
import { amountOf } from './boardConfig';

/*
 * One dollar filter on the filter card (plan.md §8.14; F19, F21; the old `bnf-filter-num-wrap`): "Monthly total ≤ $",
 * "EE-only rate ≤ $", "PCP copay ≤ $". It keeps what is typed while it is being typed ("4." stays "4.") and follows
 * the board when the value changes from elsewhere (Clear, a saved setup, another line).
 */
export default function NumberFilter({ label, title, value, onChange }) {
  const [text, setText] = useState(value == null ? '' : String(value));
  const [seen, setSeen] = useState(value);
  if (seen !== value) {
    setSeen(value);
    if (amountOf(text) !== value) setText(value == null ? '' : String(value));
  }
  return (
    <label className="bnf-filter-num-wrap" title={title || undefined}>
      {label}
      <input
        type="number"
        min="0"
        className="bnf-filter-num"
        value={text}
        onChange={(event) => {
          setText(event.target.value);
          onChange(amountOf(event.target.value));
        }}
      />
    </label>
  );
}
