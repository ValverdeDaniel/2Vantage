import { useEffect, useId, useRef, useState } from 'react';
import cx from './cx';

/**
 * A button that opens a menu of actions or links ("Stage ▾"), in the old ⬇ Download menu's look
 * (`bnf-q-dlmenu`: a small secondary button, the list under it, each item's words in bold with an optional note).
 *   label (button content; a ▾ is added), items: [{key, label, note?, href? | onSelect?, checked?, disabled?}]
 *   disabled · title · buttonClassName (replaces the trigger's classes) · ariaLabel
 * Keyboard: Enter / Space / ↓ open; ↑ ↓ Home End move; Escape closes and returns focus; Tab closes.
 * Items with `checked` (true / false) are radio items (✓ marks the current one).
 */
export default function Menu({ label, items, disabled, title, buttonClassName, ariaLabel }) {
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
    <div ref={rootRef} className="bnf-q-dlmenu">
      <button
        ref={buttonRef}
        type="button"
        className={buttonClassName || 'btn btn-secondary btn-sm'}
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
        {label} ▾
      </button>
      {open && (
        <div id={menuId} role="menu" className="bnf-q-dlmenu-list" onKeyDown={onMenuKeyDown}>
          {items.map((item) => {
            const radio = item.checked !== undefined;
            const common = {
              role: radio ? 'menuitemradio' : 'menuitem',
              'aria-checked': radio ? Boolean(item.checked) : undefined,
              'aria-disabled': item.disabled || undefined,
              tabIndex: -1,
              className: cx('bnf-q-dlmenu-item', item.disabled && 'bnf-menu-disabled'),
              title: item.title,
              onClick: (event) => select(item, event),
            };
            const words = (
              <>
                <b>
                  {radio && (item.checked ? '✓ ' : '')}
                  {item.label}
                </b>
                {item.note && <span>{item.note}</span>}
              </>
            );
            return item.href ? (
              <a key={item.key} href={item.href} {...common}>
                {words}
              </a>
            ) : (
              <button key={item.key} type="button" {...common}>
                {words}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
