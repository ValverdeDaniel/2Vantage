import { useState } from 'react';
import Button from '../../ui/Button';
import { isoIn, laterPicks } from './rowView';

/*
 * The two small forms that open under a row (I15, I24): "Later" (Bring it back: Tomorrow / In 3 days / Next week, a
 * day, an optional note) and "Log follow-up" (Called / Emailed, what was said). Old Vantage 891f1b3
 * `shared/agenda/AgendaParts.jsx` LaterForm and FollowUpForm, their words and classes; the picks start from the
 * agency's today in the payload, and a nudge's form stops the day before its link runs out (`max`).
 */
export function LaterForm({ meta, today, max, withNote = true, busy, onSave, onCancel }) {
  const tomorrow = isoIn(today, 1);
  const [until, setUntil] = useState(tomorrow);
  const [note, setNote] = useState('');
  return (
    <form
      className="bnf-ag-form"
      onSubmit={(event) => {
        event.preventDefault();
        onSave(until, note);
      }}
      onClick={(event) => event.stopPropagation()}
    >
      <span className="bnf-ag-form-label">Bring it back</span>
      {laterPicks(meta, today, max).map((pick) => (
        <button
          key={pick.label}
          type="button"
          className={`bnf-ag-pick ${until === pick.until ? 'bnf-ag-pick-on' : ''}`}
          onClick={() => setUntil(pick.until)}
        >
          {pick.label}
        </button>
      ))}
      <input
        type="date"
        min={tomorrow}
        max={max || undefined}
        value={until}
        onChange={(event) => setUntil(event.target.value)}
        aria-label="The day it comes back"
      />
      {withNote && (
        <input
          className="bnf-ag-note"
          placeholder="Why, for whoever picks it up (optional)"
          value={note}
          onChange={(event) => setNote(event.target.value)}
          aria-label="Why it waits"
        />
      )}
      <Button variant="primary" size="sm" type="submit" busy={busy} disabled={!until}>
        {busy ? 'Saving…' : 'Later'}
      </Button>
      <Button size="sm" onClick={onCancel}>
        Cancel
      </Button>
    </form>
  );
}

export function FollowUpForm({ meta, busy, onSave, onCancel }) {
  const kinds = meta?.agenda?.follow_up_kinds || [];
  const [body, setBody] = useState('');
  const [kind, setKind] = useState(kinds[0]?.key || 'call');
  return (
    <form
      className="bnf-ag-form"
      onSubmit={(event) => {
        event.preventDefault();
        onSave(body, kind);
      }}
      onClick={(event) => event.stopPropagation()}
    >
      <select value={kind} onChange={(event) => setKind(event.target.value)} aria-label="How you followed up">
        {kinds.map((option) => (
          <option key={option.key} value={option.key}>
            {option.label}
          </option>
        ))}
      </select>
      <input
        className="bnf-ag-note"
        placeholder="What was said (saved as a note on the deal)"
        value={body}
        onChange={(event) => setBody(event.target.value)}
        aria-label="What was said"
      />
      <Button variant="primary" size="sm" type="submit" busy={busy}>
        {busy ? 'Saving…' : 'Log follow-up'}
      </Button>
      <Button size="sm" onClick={onCancel}>
        Cancel
      </Button>
    </form>
  );
}
