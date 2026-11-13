import { useState } from 'react';

/*
 * The note the client reads on their link instead of our help text (B37, L122; old 891f1b3 `IntakeReviewView.jsx`
 * `NoteCell`): typed here, saved when the box is left, at most 300 characters (/api/meta/ `review.note_rule_limit`).
 * Keyed by the saved note, so a reload shows the server's.
 */
export default function RuleNote({ note, limit = 300, busy, onSave }) {
  const [draft, setDraft] = useState(null);
  const shown = draft ?? note ?? '';
  return (
    <input
      className="bnf-ireview-note"
      value={shown}
      disabled={busy}
      maxLength={limit}
      aria-label="A note they will see"
      placeholder="A note they'll see instead of our help text"
      onChange={(event) => setDraft(event.target.value)}
      onBlur={() => {
        if (draft !== null && draft.trim() !== (note || '')) onSave(draft.trim());
        setDraft(null);
      }}
    />
  );
}
