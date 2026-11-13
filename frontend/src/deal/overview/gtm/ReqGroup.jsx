/**
 * One requirement group of Card 1 (M44; old `bnf-req-group` at 891f1b3 `GetToMarketCard.jsx`): its head — the chevron,
 * ✓ or "Open", the title and the count — opens or closes the body, by click or by Enter and Space (a button to the
 * keyboard, in the old head's look, as the journey stepper's steps are); the section keeps its place when closed. Open
 * until met, then the person's toggle wins (the card holds the toggles).
 */
export default function ReqGroup({ group, open, onToggle, children }) {
  return (
    <section className={`bnf-req-group ${group.met ? 'is-done' : ''}`} aria-label={group.title}>
      <div
        role="button"
        tabIndex={0}
        className="bnf-req-head"
        aria-expanded={open}
        onClick={onToggle}
        onKeyDown={(event) => {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            onToggle();
          }
        }}
      >
        <span className={`bnf-req-chevron ${open ? 'expanded' : ''}`} aria-hidden="true">
          ▶
        </span>
        {group.met ? <span className="bb-check">✓</span> : <span className="bb-badge bb-badge-amber">Open</span>}
        <span className="bnf-req-title">{group.title}</span>
        <span className="bnf-req-count">{group.count}</span>
      </div>
      {open && <div className="bnf-req-body">{children}</div>}
    </section>
  );
}
