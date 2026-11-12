import { useEffect, useRef, useState } from 'react';
import { useUpdateDeal } from '../../api/deals';
import { errorText } from '../../lib/errors';
import SaveStatus from '../../ui/SaveStatus';

/**
 * One typed fact in the header chips, as the effective date is edited (M24's click-to-edit rules): "Potential deal
 * size $250,000 ✎" or "Agent of record Dana Lee (default) ✎". Click to edit; Enter or Save saves, Escape or Cancel
 * leaves; an unchanged value is never sent; blank clears. The server cleans what is typed and says what is wrong.
 *   field: the PATCH key · label · shown: the words when set · fallback: the words when blank (in grey) · initial: what
 *   the input starts with · placeholder · hint: the button's tooltip
 */
export default function HeaderFact({ deal, field, label, shown, fallback, initial, placeholder, hint }) {
  const update = useUpdateDeal(deal.id);
  const [draft, setDraft] = useState(null); // null: not editing
  const buttonRef = useRef(null);
  const refocus = useRef(false);

  useEffect(() => {
    if (draft === null && refocus.current) {
      refocus.current = false;
      buttonRef.current?.focus();
    }
  }, [draft]);

  function done() {
    refocus.current = true;
    setDraft(null);
  }

  function cancel() {
    update.reset();
    done();
  }

  function save() {
    const value = draft.trim();
    if (value === initial) {
      done();
      return;
    }
    update.mutate({ [field]: value }, { onSuccess: done });
  }

  if (draft === null) {
    return (
      <span className="bb-drop-meta">
        {label}{' '}
        <button
          ref={buttonRef}
          type="button"
          className="bnf-wq-namebtn bb-drop-meta"
          title={hint}
          aria-label={`${label}: ${shown || fallback || 'not set'}. Change`}
          onClick={() => {
            update.reset();
            setDraft(initial);
          }}
        >
          {shown || (fallback ? <span className="bb-drop-meta">{fallback}</span> : 'not set')} ✎
        </button>{' '}
        <SaveStatus mutation={update} />
      </span>
    );
  }

  return (
    <form
      className="bnf-ov-chips"
      noValidate
      onSubmit={(event) => {
        event.preventDefault();
        save();
      }}
    >
      <span className="bb-drop-meta">{label}</span>
      <input
        className="bnf-intake-input"
        aria-label={label}
        aria-invalid={update.isError || undefined}
        value={draft}
        placeholder={placeholder}
        onChange={(event) => setDraft(event.target.value)}
        autoFocus
        onKeyDown={(event) => {
          if (event.key === 'Escape') {
            event.preventDefault();
            cancel();
          }
        }}
      />
      <button type="submit" className="btn btn-primary btn-sm" disabled={update.isPending}>
        Save
      </button>
      <button type="button" className="btn btn-secondary btn-sm" onClick={cancel}>
        Cancel
      </button>
      {update.isError && (
        <span role="alert" className="bb-rose">
          {errorText(update.error)}
        </span>
      )}
    </form>
  );
}
