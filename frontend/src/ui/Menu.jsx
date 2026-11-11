import { useEffect, useId, useRef, useState } from 'react';
import cx from './cx';
import styles from './Menu.module.css';

/**
 * A button that opens a menu of actions or links ("Stage ▾", the user menu).
 *   label (button content; a ▾ is added), items: [{key, label, href? | onSelect?, checked?, disabled?}]
 *   align: 'start' | 'end' · disabled · title · buttonClassName (restyle the trigger) · ariaLabel
 * Keyboard: Enter / Space / ↓ open; ↑ ↓ Home End move; Escape closes and returns focus; Tab closes.
 * Items with `checked` (true / false) are radio items (✓ marks the current one).
 */
export default function Menu({ label, items, align = 'start', disabled, title, buttonClassName, ariaLabel }) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef(null);
  const buttonRef = useRef(null);
  const menuId = useId();

  useEffect(() => {
    if (!open) return undefined;
    const menu = rootRef.current?.querySelector('[role="menu"]');
    const current = menu?.querySelector('[aria-checked="true"]:not([aria-disabled="true"])');
    const first = menu?.querySelector('[role^="menuitem"]:not([aria-disabled="true"])');
    (current || first)?.focus();
    function onPointerDown(event) {
      if (!rootRef.current?.contains(event.target)) setOpen(false);
    }
    document.addEventListener('mousedown', onPointerDown);
    return () => document.removeEventListener('mousedown', onPointerDown);
  }, [open]);

  function close({ focusButton = true } = {}) {
    setOpen(false);
    if (focusButton) buttonRef.current?.focus();
  }

  function onMenuKeyDown(event) {
    const entries = [...event.currentTarget.querySelectorAll('[role^="menuitem"]:not([aria-disabled="true"])')];
    const index = entries.indexOf(document.activeElement);
    const move = { ArrowDown: index + 1, ArrowUp: index - 1, Home: 0, End: entries.length - 1 }[event.key];
    if (move !== undefined) {
      event.preventDefault();
      entries[(move + entries.length) % entries.length]?.focus();
    } else if (event.key === 'Escape') {
      event.preventDefault();
      event.stopPropagation();
      close();
    } else if (event.key === 'Tab') {
      close({ focusButton: false });
    }
  }

  function select(item, event) {
    if (item.disabled) {
      event.preventDefault();
      return;
    }
    close({ focusButton: !item.href });
    item.onSelect?.();
  }

  return (
    <div ref={rootRef} className={styles.root}>
      <button
        ref={buttonRef}
        type="button"
        className={cx(styles.trigger, buttonClassName)}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={open ? menuId : undefined}
        aria-label={ariaLabel}
        disabled={disabled}
        title={title}
        onClick={() => setOpen((value) => !value)}
        onKeyDown={(event) => {
          if (event.key === 'ArrowDown' && !open) {
            event.preventDefault();
            setOpen(true);
          }
        }}
      >
        {label}
        <span aria-hidden="true" className={styles.caret}>
          ▾
        </span>
      </button>
      {open && (
        <ul id={menuId} role="menu" className={cx(styles.menu, styles[align])} onKeyDown={onMenuKeyDown}>
          {items.map((item) => {
            const radio = item.checked !== undefined;
            const common = {
              role: radio ? 'menuitemradio' : 'menuitem',
              'aria-checked': radio ? Boolean(item.checked) : undefined,
              'aria-disabled': item.disabled || undefined,
              tabIndex: -1,
              className: cx(styles.item, item.disabled && styles.disabled),
              onClick: (event) => select(item, event),
            };
            return (
              <li key={item.key} role="none">
                {item.href ? (
                  <a href={item.href} {...common}>
                    {item.label}
                  </a>
                ) : (
                  <button type="button" {...common}>
                    <span className={styles.check} aria-hidden="true">
                      {item.checked ? '✓' : ''}
                    </span>
                    {item.label}
                  </button>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
