import { useEffect, useRef, useState } from 'react';

/*
 * The ⬇ menu (G56; the old QuestionnaireTab DownloadMenu, words and classes kept): one button in place of three, each
 * item saying what it is. It closes on a pick, a click outside or Escape. "Carrier PDF (Acrobat)" is not offered
 * until the XFA copy is built (G58, deferred; OQ57).
 *   items: [{key, label, detail, run}] · busy: the button reads "Preparing…" while a file builds
 */
export default function DownloadMenu({ items, busy }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  useEffect(() => {
    if (!open) return undefined;
    const away = (event) => {
      if (ref.current && !ref.current.contains(event.target)) setOpen(false);
    };
    document.addEventListener('mousedown', away);
    return () => document.removeEventListener('mousedown', away);
  }, [open]);
  return (
    <div
      className="bnf-q-dlmenu"
      ref={ref}
      onKeyDown={(event) => {
        if (event.key === 'Escape') setOpen(false);
      }}
    >
      <button
        type="button"
        className="btn btn-secondary btn-sm"
        aria-haspopup="menu"
        aria-expanded={open}
        disabled={busy}
        onClick={() => setOpen((value) => !value)}
      >
        {busy ? 'Preparing…' : '⬇ Download ▾'}
      </button>
      {open && (
        <div className="bnf-q-dlmenu-list" role="menu">
          {items.map((item) => (
            <button
              key={item.key}
              type="button"
              role="menuitem"
              className="bnf-q-dlmenu-item"
              onClick={() => {
                setOpen(false);
                item.run();
              }}
            >
              <b>{item.label}</b>
              <span>{item.detail}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
