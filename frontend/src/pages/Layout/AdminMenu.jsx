import { useEffect, useRef, useState } from 'react';

/**
 * The top bar's Admin group in the old menu's look (navbar-menu, D-073): a trigger over a panel. Users and agency
 * settings live in Django admin (rule 9, A5), so the panel's one item opens /admin/. Closes on an outside press, an
 * item click and Escape (focus back to the trigger); the top bar remounts it on every route change.
 */
export default function AdminMenu() {
  const [open, setOpen] = useState(false);
  const menuRef = useRef(null);
  const triggerRef = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    menuRef.current?.querySelector('[role="menuitem"]')?.focus();
    function onPointerDown(event) {
      if (!menuRef.current?.contains(event.target)) setOpen(false);
    }
    document.addEventListener('pointerdown', onPointerDown);
    return () => document.removeEventListener('pointerdown', onPointerDown);
  }, [open]);

  function onKeyDown(event) {
    if (event.key === 'Escape' && open) {
      event.preventDefault();
      setOpen(false);
      triggerRef.current?.focus();
    } else if (event.key === 'ArrowDown' && !open) {
      event.preventDefault();
      setOpen(true);
    }
  }

  return (
    <div className="navbar-menu" ref={menuRef} onKeyDown={onKeyDown}>
      <button
        type="button"
        ref={triggerRef}
        className={open ? 'navbar-menu-trigger is-open' : 'navbar-menu-trigger'}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls="navbar-admin-menu"
        onClick={() => setOpen((value) => !value)}
      >
        Admin
        <span className="navbar-menu-caret" aria-hidden="true">
          ▾
        </span>
      </button>
      {open && (
        <div className="navbar-menu-panel" id="navbar-admin-menu" role="menu" aria-label="Admin">
          <a href="/admin/" role="menuitem" onClick={() => setOpen(false)}>
            Django admin
          </a>
        </div>
      )}
    </div>
  );
}
