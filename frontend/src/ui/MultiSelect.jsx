import { useEffect, useId, useRef, useState } from 'react';
import cx from './cx';
import styles from './MultiSelect.module.css';

/**
 * Pick several options from a searchable list; the picks show as removable chips (in `options` order).
 *   options: [{value, label}] · value: [values] · onChange(nextValues)
 *   onRemove(value): optional; called instead of onChange when a pick is removed (e.g. to confirm first)
 *   addLabel: optional. Given, the search box hides behind a button ("+ Line") that opens it as a popover;
 *             without it the search box is always shown below the chips (forms).
 *   id, aria-describedby, aria-invalid: for the search box (Field passes them) · label: accessible name when there
 *   is no <label> · placeholder · disabled · emptyText (nothing selected) · noMatchText
 * Keyboard in the search box: ↑ ↓ move, Enter toggles, Escape closes, Backspace on empty removes the last chip.
 */
export default function MultiSelect({
  options,
  value,
  onChange,
  onRemove,
  addLabel,
  id,
  label,
  placeholder = 'Search…',
  disabled = false,
  emptyText,
  noMatchText = 'No matches.',
  'aria-describedby': describedBy,
  'aria-invalid': invalid,
}) {
  const autoId = useId();
  const inputId = id || `${autoId}-search`;
  const listId = `${autoId}-list`;
  const popover = Boolean(addLabel);
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const rootRef = useRef(null);
  const inputRef = useRef(null);
  const addRef = useRef(null);

  const selected = new Set(value);
  const labels = new Map(options.map((option) => [option.value, option.label]));
  const chips = ordered(value);
  const needle = query.trim().toLowerCase();
  const matches = needle ? options.filter((o) => o.label.toLowerCase().includes(needle)) : options;
  const activeIndex = Math.min(active, Math.max(matches.length - 1, 0));
  const optionId = (index) => `${autoId}-option-${index}`;

  useEffect(() => {
    if (!open) return undefined;
    if (popover) inputRef.current?.focus();
    function onPointerDown(event) {
      if (!rootRef.current?.contains(event.target)) setOpen(false);
    }
    document.addEventListener('mousedown', onPointerDown);
    return () => document.removeEventListener('mousedown', onPointerDown);
  }, [open, popover]);

  useEffect(() => {
    if (open) document.getElementById(optionId(activeIndex))?.scrollIntoView?.({ block: 'nearest' });
  });

  function ordered(values) {
    const set = new Set(values);
    return [...options.filter((o) => set.has(o.value)).map((o) => o.value), ...values.filter((v) => !labels.has(v))];
  }

  function remove(item) {
    if (onRemove) onRemove(item);
    else onChange(value.filter((v) => v !== item));
  }

  function toggle(option) {
    if (selected.has(option.value)) remove(option.value);
    else onChange(ordered([...value, option.value]));
  }

  function close({ refocus = true } = {}) {
    setOpen(false);
    setQuery('');
    if (popover && refocus) addRef.current?.focus();
  }

  function onKeyDown(event) {
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault();
      if (!open) setOpen(true);
      else if (matches.length) setActive((activeIndex + (event.key === 'ArrowDown' ? 1 : -1) + matches.length) % matches.length);
    } else if (event.key === 'Enter') {
      if (open && matches[activeIndex]) {
        event.preventDefault();
        toggle(matches[activeIndex]);
      }
    } else if (event.key === 'Escape') {
      if (open || query) {
        // Keep an enclosing dialog open: this Escape only closes the list.
        event.preventDefault();
        event.stopPropagation();
        close();
      }
    } else if (event.key === 'Backspace' && !query && !popover && chips.length) {
      remove(chips[chips.length - 1]);
    } else if (event.key === 'Tab' && popover) {
      close({ refocus: false });
    }
  }

  const search = (
    <input
      ref={inputRef}
      id={inputId}
      type="text"
      role="combobox"
      className={styles.search}
      value={query}
      placeholder={placeholder}
      disabled={disabled}
      autoComplete="off"
      aria-label={label}
      aria-describedby={describedBy}
      aria-invalid={invalid}
      aria-expanded={open}
      aria-controls={listId}
      aria-autocomplete="list"
      aria-activedescendant={open && matches.length ? optionId(activeIndex) : undefined}
      onChange={(event) => {
        setQuery(event.target.value);
        setActive(0);
        setOpen(true);
      }}
      onClick={() => setOpen(true)}
      onKeyDown={onKeyDown}
    />
  );

  const list = open && (
    <ul id={listId} role="listbox" aria-multiselectable="true" aria-label={label} className={styles.list}>
      {matches.length === 0 && <li className={styles.noMatch}>{noMatchText}</li>}
      {matches.map((option, index) => (
        <li
          key={option.value}
          id={optionId(index)}
          role="option"
          aria-selected={selected.has(option.value)}
          className={cx(styles.option, index === activeIndex && styles.active)}
          onMouseDown={(event) => event.preventDefault()}
          onMouseEnter={() => setActive(index)}
          onClick={() => toggle(option)}
        >
          <span className={styles.check} aria-hidden="true">
            {selected.has(option.value) ? '✓' : ''}
          </span>
          {option.label}
        </li>
      ))}
    </ul>
  );

  return (
    <div ref={rootRef} className={cx(styles.root, popover && styles.inlineRoot)}>
      <ul className={styles.chips} aria-label={label ? `${label}: selected` : 'Selected'}>
        {chips.length === 0 && emptyText && <li className={styles.empty}>{emptyText}</li>}
        {chips.map((item) => (
          <li key={item} className={styles.chip}>
            <span>{labels.get(item) || item}</span>
            <button
              type="button"
              className={styles.remove}
              aria-label={`Remove ${labels.get(item) || item}`}
              title={`Remove ${labels.get(item) || item}`}
              disabled={disabled}
              onClick={() => remove(item)}
            >
              <span aria-hidden="true">✕</span>
            </button>
          </li>
        ))}
        {popover && (
          <li className={styles.addItem}>
            <button
              ref={addRef}
              type="button"
              className={styles.add}
              disabled={disabled}
              aria-expanded={open}
              onClick={() => (open ? close() : setOpen(true))}
            >
              {addLabel}
            </button>
            {open && (
              <div className={styles.popover}>
                {search}
                {list}
              </div>
            )}
          </li>
        )}
      </ul>
      {!popover && (
        <div className={styles.inlineSearch}>
          {search}
          {list}
        </div>
      )}
    </div>
  );
}
