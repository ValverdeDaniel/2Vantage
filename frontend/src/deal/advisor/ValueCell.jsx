import { useRef, useState } from 'react';
import { errorText } from '../../lib/errors';
import { formatWhen } from '../../lib/format';
import cx from '../../ui/cx';
import { displayValue, ORIGIN_ICON } from './display';
import styles from './PlanTable.module.css';

/**
 * One plan value, edited in place (plan.md §8.11). Shows the formatted value; on focus the stored text. Saves on
 * blur (choices save on change) when the text changed; the server cleans it and answers with the cleaned value or
 * a message, shown under the cell. A required blank cell has a red outline and says "Required" to screen readers.
 */
export default function ValueCell({ plan, field, update, labelId }) {
  const raw = plan.values?.[field.key] ?? '';
  const [draft, setDraft] = useState(null);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  // Escape blurs the input; the blur handler still sees this render's draft, so it reads this flag instead.
  const cancelled = useRef(false);
  const status = plan.status?.[field.key];
  const source = plan.sources?.[field.key];

  async function commit(next) {
    setDraft(null);
    if (next === raw) return;
    setSaving(true);
    setError('');
    try {
      await update.mutateAsync({ planId: plan.id, changes: { values: { [field.key]: next } } });
    } catch (err) {
      const message = err?.response?.data?.values?.[field.key];
      setError(message || errorText(err));
    } finally {
      setSaving(false);
    }
  }

  const common = {
    'aria-labelledby': labelId,
    'aria-invalid': status === 'missing' || error ? true : undefined,
    className: cx(styles.input, status === 'missing' && styles.missing, error && styles.invalid),
    disabled: saving,
  };

  let control;
  if (field.type === 'choice' || field.type === 'yesno') {
    const options =
      field.type === 'yesno' ? [{ key: 'Yes', label: 'Yes' }, { key: 'No', label: 'No' }] : field.choices || [];
    control = (
      <select {...common} value={raw} onChange={(event) => commit(event.target.value)}>
        <option value="">—</option>
        {options.map((option) => (
          <option key={option.key} value={option.key}>
            {option.label}
          </option>
        ))}
      </select>
    );
  } else {
    control = (
      <input
        {...common}
        type="text"
        value={draft ?? displayValue(field, raw)}
        onFocus={() => setDraft(String(raw))}
        onChange={(event) => setDraft(event.target.value)}
        onBlur={() => {
          if (cancelled.current) cancelled.current = false;
          else if (draft !== null) commit(draft.trim());
        }}
        onKeyDown={(event) => {
          if (event.key === 'Enter') event.currentTarget.blur();
          if (event.key === 'Escape') {
            cancelled.current = true;
            setDraft(null);
            event.currentTarget.blur();
          }
        }}
      />
    );
  }

  const sourceTitle = source
    ? `${source.origin}${source.at ? ` · ${formatWhen(source.at)}` : ''}${source.cell ? ` · ${source.cell}` : ''}`
    : '';
  return (
    <td className={cx(styles.cell, status === 'to_check' && styles.toCheck)}>
      <div className={styles.cellInner}>
        {control}
        {source && source.origin !== 'typed' && (
          <span className={styles.source} title={sourceTitle} aria-label={`Source: ${sourceTitle}`}>
            {ORIGIN_ICON[source.origin] ?? '•'}
          </span>
        )}
      </div>
      {status === 'missing' && !error && <span className={styles.srOnly}>Required</span>}
      {error && (
        <p className={styles.cellError} role="alert">
          <span aria-hidden="true">⚠ </span>
          {error}
        </p>
      )}
    </td>
  );
}
