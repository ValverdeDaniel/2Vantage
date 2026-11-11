import { useEffect, useRef, useState } from 'react';
import { useUpdateDeal } from '../../api/deals';
import { errorText } from '../../lib/errors';
import { formatDate } from '../../lib/format';
import Button from '../../ui/Button';
import DateInput from '../../ui/DateInput';
import SaveStatus from '../../ui/SaveStatus';
import styles from './HeaderFields.module.css';

/** "Effective 01/01/2027 ✎": click to edit inline; Enter or Save saves, Escape or Cancel leaves it. */
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
      <span className={styles.fact}>
        <span className={styles.label}>Effective</span>
        <button
          ref={buttonRef}
          type="button"
          className={styles.inlineEdit}
          aria-label={`Effective date: ${shown || 'not set'}. Change`}
          onClick={() => {
            update.reset();
            setDraft(deal.effective_date || '');
          }}
        >
          {shown || <span className={styles.placeholder}>not set</span>}
          <span aria-hidden="true" className={styles.pencil}>
            ✎
          </span>
        </button>
        <SaveStatus mutation={update} />
      </span>
    );
  }

  return (
    <form
      className={styles.inlineForm}
      noValidate
      onSubmit={(event) => {
        event.preventDefault();
        save();
      }}
    >
      <span className={styles.label}>Effective</span>
      <DateInput
        size="sm"
        className={styles.dateInput}
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
      <Button size="sm" type="submit" variant="primary" busy={update.isPending}>
        Save
      </Button>
      <Button size="sm" variant="ghost" onClick={cancel}>
        Cancel
      </Button>
      {update.isError && (
        <span role="alert" className={styles.error}>
          {errorText(update.error)}
        </span>
      )}
    </form>
  );
}
