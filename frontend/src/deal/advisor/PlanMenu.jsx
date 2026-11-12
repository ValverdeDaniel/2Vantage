import { useEffect, useId, useRef, useState } from 'react';
import cx from '../../ui/cx';

/**
 * A plan column's ⋯ menu, in the old Proposal grid's look (ComparisonGrid.jsx at 891f1b3: `bnf-plan-menu-btn`
 * opening a `bnf-plan-menu` under the column head, `bnf-menu-danger` for Delete, `bnf-menu-disabled` greyed).
 *   label (the trigger's accessible name), items: [{key, label, onSelect, disabled?, danger?}]
 * Keyboard: Enter / Space / ↓ open; ↑ ↓ Home End move; Enter or Space picks; Escape closes and returns focus.
 */
export default function PlanMenu({ label, items }) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef(null);
  const buttonRef = useRef(null);
  const menuId = useId();

  useEffect(() => {
    if (!open) return undefined;
    rootRef.current?.querySelector('[role="menuitem"]:not([aria-disabled="true"])')?.focus();
    function onPointerDown(event) {
      if (!rootRef.current?.contains(event.target)) setOpen(false);
    }
    document.addEventListener('mousedown', onPointerDown);
    return () => document.removeEventListener('mousedown', onPointerDown);
  }, [open]);

  function close() {
    setOpen(false);
    buttonRef.current?.focus();
  }

  function pick(item) {
    if (item.disabled) return;
    close();
    item.onSelect();
  }

  function onMenuKeyDown(event) {
    const entries = [...event.currentTarget.querySelectorAll('[role="menuitem"]:not([aria-disabled="true"])')];
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
      setOpen(false);
    }
  }

  return (
    <span ref={rootRef}>
      <button
        ref={buttonRef}
        type="button"
        className="bnf-plan-menu-btn"
        aria-label={label}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={open ? menuId : undefined}
        onClick={() => setOpen((value) => !value)}
        onKeyDown={(event) => {
          if (event.key === 'ArrowDown' && !open) {
            event.preventDefault();
            setOpen(true);
          }
        }}
      >
        ⋯
      </button>
      {open && (
        <div id={menuId} role="menu" aria-label={label} className="bnf-plan-menu" onKeyDown={onMenuKeyDown}>
          {items.map((item) => (
            <div
              key={item.key}
              role="menuitem"
              tabIndex={-1}
              aria-disabled={item.disabled || undefined}
              className={cx(item.disabled && 'bnf-menu-disabled', item.danger && 'bnf-menu-danger')}
              onClick={() => pick(item)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' || event.key === ' ') {
                  event.preventDefault();
                  pick(item);
                }
              }}
            >
              {item.label}
            </div>
          ))}
        </div>
      )}
    </span>
  );
}
