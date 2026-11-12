/*
 * The plan finder's box (plan.md §8.14; F14–F16; the old `bnf-advisor-finder`): one box for a plan's name, number,
 * carrier (or its nickname, "UHC"), network, plan type or code. Enter jumps to the first match, Esc clears (and stops
 * there, so it closes nothing else). Under it, "Also matches 2 on Dental": each chip switches to that line and keeps
 * the words; the box keeps the focus, so the words can be refined in place.
 */
export default function FinderBox({ value, onChange, onEnter, others, inputRef, onPickLine }) {
  const query = value.trim();
  return (
    <div className="bnf-advisor-finder">
      <div className="bnf-advisor-search">
        <input
          type="text"
          className="bnf-filter-text"
          placeholder="Find a plan: name, carrier, code…"
          aria-label="Find a plan by name, carrier, plan code, network or plan type"
          autoComplete="off"
          spellCheck={false}
          ref={inputRef}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter') {
              event.preventDefault();
              onEnter();
            } else if (event.key === 'Escape' && value !== '') {
              event.preventDefault();
              event.stopPropagation();
              onChange('');
            }
          }}
        />
      </div>
      {others.length > 0 && (
        <div className="bnf-find-lines" role="group" aria-label="Matches on the other lines">
          <span className="bnf-find-lead">Also matches</span>
          {others.map((hit) => (
            <button
              key={hit.line}
              type="button"
              className="bnf-find-chip"
              title={`Switch to ${hit.label} and keep “${query}”`}
              onClick={() => {
                onPickLine(hit.line);
                inputRef.current?.focus({ preventScroll: true });
              }}
            >
              {hit.count} on {hit.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
