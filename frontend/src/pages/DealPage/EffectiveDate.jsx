import { useEffect, useRef, useState } from 'react';
import { useUpdateDeal } from '../../api/deals';
import { errorText } from '../../lib/errors';
import { formatDate } from '../../lib/format';
import DateInput from '../../ui/DateInput';
import SaveStatus from '../../ui/SaveStatus';

/** "Effective 01/01/2027 ✎" in the header chips: click to edit inline; Enter or Save saves, Escape or Cancel leaves. */
export default function EffectiveDate({ deal }) {
  const update = useUpdateDeal(deal.id);
  const [draft, setDraft] = useState(null); // null: not editing
  const shown = formatDate(deal.effective_date);
  const buttonRef = useRef(null);
  const refocus = useRef(false);

  useEffect(() => {
    // Leaving the editor (Save, Cancel, Escape) puts focus back on the date it replaced.
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
    const value = draft || null;
    if (value === (deal.effective_date || null)) {
      done();
      return;
    }
    update.mutate({ effective_date: value }, { onSuccess: done });
  }

  if (draft === null) {
    return (
      <span className="bb-drop-meta">
        Effective{' '}
        <button
          ref={buttonRef}
          type="button"
          className="bnf-wq-namebtn bb-drop-meta"
          aria-label={`Effective date: ${shown || 'not set'}. Change`}
          onClick={() => {
            update.reset();
            setDraft(deal.effective_date || '');
          }}
        >
          {shown || 'not set'} ✎
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
      <span className="bb-drop-meta">Effective</span>
      <DateInput
        className="bnf-intake-input"
        aria-label="Effective date"
        aria-invalid={update.isError || undefined}
        value={draft}
        onValueChange={setDraft}
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
