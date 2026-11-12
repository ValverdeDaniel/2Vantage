import { forwardRef } from 'react';

/*
 * The box a queue item opens for a typed value (E correct, A on an item that needs one) or a note (old 891f1b3
 * `ReviewQueue.jsx` `rr-qi-field`): Enter saves or sends, Shift+Enter is a new line in a note, Esc cancels. The note's
 * audience toggle and quick replies join with the threads (slice 56).
 */
const QueueField = forwardRef(function QueueField({ mode, draft, onDraft, onSubmit, onCancel }, ref) {
  const onKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      onSubmit();
    } else if (event.key === 'Escape') {
      event.preventDefault();
      onCancel();
      event.target.blur();
    }
  };
  const isValue = mode.kind === 'value';
  return (
    <div className="rr-qi-field">
      <label htmlFor="rr-qi-input">
        {mode.label || (isValue ? 'Correct value' : 'Note')}
        {!isValue && !mode.required && <span className="rr-qi-optional"> (optional)</span>}
      </label>
      {isValue ? (
        <input
          id="rr-qi-input"
          ref={ref}
          className="bnf-intake-input"
          value={draft}
          placeholder={mode.placeholder || ''}
          onChange={(event) => onDraft(event.target.value)}
          onKeyDown={onKeyDown}
        />
      ) : (
        <textarea
          id="rr-qi-input"
          ref={ref}
          value={draft}
          placeholder={mode.placeholder || ''}
          onChange={(event) => onDraft(event.target.value)}
          onKeyDown={onKeyDown}
        />
      )}
      <div className="rr-qi-hint">
        {isValue ? 'Enter to save' : 'Enter to send · Shift+Enter for a new line'}
        {' · Esc to cancel'}
      </div>
    </div>
  );
});

export default QueueField;
