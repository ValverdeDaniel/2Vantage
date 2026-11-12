import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';

/*
 * "＋ Dep" on an employee's row (plan.md §8.10; C7; D-168; the old CensusGrid's AddDependentMenu at 891f1b3): who the
 * new dependent is, from the relationship column's own choices (/api/meta/), so the row is born with an answer the
 * validator and the carrier files read. The list is portalled to <body> at the button: the roster scrolls and would
 * clip it on the last rows. React events still bubble through a portal to the grid's keys, so the list stops them.
 */
export default function AddDependentMenu({ name, choices, onPick }) {
  const [at, setAt] = useState(null); // the list's fixed position while open
  const buttonRef = useRef(null);
  const listRef = useRef(null);

  useEffect(() => {
    if (!at) return undefined;
    const close = () => setAt(null);
    const away = (event) => {
      if (listRef.current?.contains(event.target) || buttonRef.current?.contains(event.target)) return;
      close();
    };
    document.addEventListener('mousedown', away);
    window.addEventListener('scroll', close, true); // any scroll moves the button out from under a fixed list
    window.addEventListener('resize', close);
    listRef.current?.querySelector('button')?.focus({ preventScroll: true });
    return () => {
      document.removeEventListener('mousedown', away);
      window.removeEventListener('scroll', close, true);
      window.removeEventListener('resize', close);
    };
  }, [at]);

  function toggle() {
    if (at) {
      setAt(null);
      return;
    }
    const rect = buttonRef.current.getBoundingClientRect();
    const tall = 40 + choices.length * 32; // below the button, or above it when the list would run off the page
    setAt(
      rect.bottom + 4 + tall > window.innerHeight - 8
        ? { left: rect.left, bottom: window.innerHeight - rect.top + 4 }
        : { left: rect.left, top: rect.bottom + 4 },
    );
  }

  const stop = (event) => event.stopPropagation();
  return (
    <>
      <button
        ref={buttonRef}
        type="button"
        className="bnf-dep-add"
        title={`Add a spouse, child or domestic partner of ${name}`}
        aria-haspopup="menu"
        aria-expanded={Boolean(at)}
        onClick={toggle}
      >
        ＋ Dep
      </button>
      {at &&
        createPortal(
          <div
            ref={listRef}
            className="bnf-dep-menu"
            role="menu"
            style={at}
            onMouseDown={stop}
            onClick={stop}
            onKeyDown={(event) => {
              stop(event);
              if (event.key === 'Escape') {
                setAt(null);
                buttonRef.current?.focus();
              }
              if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
                event.preventDefault();
                const items = [...listRef.current.querySelectorAll('button')];
                const index = items.indexOf(document.activeElement);
                const step = event.key === 'ArrowDown' ? 1 : -1;
                items[(index + step + items.length) % items.length]?.focus();
              }
            }}
          >
            <div className="bnf-dep-menu-head">Add to {name}</div>
            {choices.map((choice) => (
              <button
                key={choice.value}
                type="button"
                role="menuitem"
                className="bnf-dep-menu-item"
                onClick={() => {
                  setAt(null);
                  onPick(choice.value);
                }}
              >
                {choice.label}
              </button>
            ))}
          </div>,
          document.body,
        )}
    </>
  );
}
