import { useEffect, useRef, useState } from 'react';
import { isTyping } from '../../valuereview/keys';

/*
 * Find in the scanned data (plan.md §8.16; E60–E64, D127; the old ScanFindBar): one box over whatever the Scanned data
 * panel shows from the file(s) in scope, the Grid or the List. Every match is marked and the grid stays whole; the box
 * says "3 of 20", and Enter / Shift+Enter (or ▲ ▼) step to the next or previous one. "Only matches" hides the plans and
 * rows with none. Escape hands the current match to the Grid or the List, selected, so A, I, C, U and F act on it at
 * once. The word rule, carrier nicknames included, is the Advisor finder's (src/lib/findText.js).
 *
 * The box keeps its own text and tells the panel a beat after typing stops (one quote file can hold 7,000 cells, and a
 * grid render per keystroke would lag the typing). Ctrl/Cmd+F lands here while the box shows; pressed again from the
 * box, it is the browser's own find. Reads only, writes nothing, and the words never reach a URL (Q.8).
 */

const SETTLE_MS = 120;

export default function FindBar({ query, onQuery, total = 0, at = 0, onStep, only = false, onOnly, onLeave }) {
  // The box owns its text; the panel hears it a beat after typing stops. A new scope remounts the panel, box and all.
  const [text, setText] = useState(query);
  const inputRef = useRef(null);
  const sent = useRef(query); // the last words this box sent

  const send = (value) => {
    sent.current = value;
    onQuery(value);
  };
  useEffect(() => {
    if (text === sent.current) return undefined;
    const timer = setTimeout(() => {
      sent.current = text;
      onQuery(text);
    }, SETTLE_MS);
    return () => clearTimeout(timer);
  }, [text, onQuery]);

  // Ctrl/Cmd+F: this box, unless focus is already in it (then the browser's find) or in another field being typed in
  // (an ✎ Edit cell keeps its keys).
  useEffect(() => {
    const onKeyDown = (event) => {
      if (!(event.ctrlKey || event.metaKey) || event.altKey || event.shiftKey) return;
      if (String(event.key).toLowerCase() !== 'f' || event.defaultPrevented) return;
      const box = inputRef.current;
      const typing = isTyping(event.target) && !['checkbox', 'radio'].includes(event.target.type);
      if (!box || event.target === box || typing) return;
      event.preventDefault();
      box.focus();
      box.select();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, []);

  const onKeyDown = (event) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      // A query still settling is sent first: Enter then means "find this".
      if (text !== sent.current) send(text);
      else if (total) onStep(event.shiftKey ? -1 : 1);
    } else if (event.key === 'Escape' && (text || query)) {
      event.preventDefault();
      event.stopPropagation();
      setText('');
      sent.current = '';
      onLeave();
    }
  };

  const clear = () => {
    setText('');
    send('');
    inputRef.current?.focus();
  };

  const searching = Boolean(query.trim());
  return (
    <div className="sf-bar" role="search">
      <input
        ref={inputRef}
        type="text"
        className="bnf-filter-text sf-input"
        value={text}
        onChange={(event) => setText(event.target.value)}
        onKeyDown={onKeyDown}
        placeholder="Find in the scanned data: plan, carrier, benefit, value…"
        aria-label="Find in the scanned data"
        title="Find a plan, a benefit or a value in what was read from the selected file (Ctrl+F). Enter steps to the next match, Shift+Enter back, Esc selects it."
        spellCheck={false}
        autoComplete="off"
      />
      {searching && (
        <span className="sf-count" role="status">
          {total ? `${at + 1} of ${total}` : 'No matches'}
        </span>
      )}
      <button
        type="button"
        className="btn btn-sm btn-secondary sf-step"
        disabled={!total}
        onClick={() => onStep(-1)}
        aria-label="Previous match"
        title="Previous match (Shift+Enter)"
      >
        ▲
      </button>
      <button
        type="button"
        className="btn btn-sm btn-secondary sf-step"
        disabled={!total}
        onClick={() => onStep(1)}
        aria-label="Next match"
        title="Next match (Enter)"
      >
        ▼
      </button>
      <label className="sf-only" title="Hide the plans and rows with no match">
        <input type="checkbox" checked={only} disabled={!searching} onChange={(event) => onOnly(event.target.checked)} />
        Only matches
      </label>
      {text && (
        <button type="button" className="bnf-linklike sf-clear" onClick={clear} aria-label="Clear the search" title="Clear the search">
          ✕
        </button>
      )}
    </div>
  );
}
