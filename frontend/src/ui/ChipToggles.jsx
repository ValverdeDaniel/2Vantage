import cx from './cx';

/**
 * Pick several from a short list, as the old intake's multi-choice chips (`bnf-multi-chips`, `bnf-chip`,
 * `bnf-chip-on`): each option is a toggle button. Replaces 2V's MultiSelect.
 *   options: [{value, label, disabled?}], value: [values], onChange(nextValues), emptyText (no options),
 *   plus aria-labelledby / aria-describedby from <Field group>.
 */
export default function ChipToggles({ options, value = [], onChange, emptyText = 'None to choose from.', ...rest }) {
  if (!options.length) return <div className="bb-account-sub">{emptyText}</div>;
  const chosen = new Set(value);
  return (
    <div role="group" className="bnf-multi-chips" {...rest}>
      {options.map((option) => {
        const on = chosen.has(option.value);
        return (
          <button
            key={option.value}
            type="button"
            className={cx('bnf-chip', on && 'bnf-chip-on')}
            aria-pressed={on}
            disabled={option.disabled}
            onClick={() =>
              onChange(on ? value.filter((v) => v !== option.value) : [...value, option.value])
            }
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
