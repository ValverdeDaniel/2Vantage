import { useState } from 'react';

/** A box that saves on blur when its text changed (K26). It never disables while a save is out (bug 3): what is typed
 *  stays on screen, and the stored value shows again once the person leaves the box. */
function useBox(stored, onSave) {
  const [text, setText] = useState(null); // while typing, else null
  return {
    value: text ?? stored ?? '',
    onChange: (event) => setText(event.target.value),
    onBlur: () => {
      if (text === null) return;
      if (text !== (stored ?? '')) onSave(text);
      setText(null);
    },
  };
}

/*
 * The request's free fields (plan.md §8.12; K26; old CarriersTab.jsx RequestPanel at 891f1b3, same classes and words):
 * Other carriers (≤ 300), Quotes due back (a date) and Notes for the carriers (≤ 2,000).
 */
export default function RequestFields({ request, limits, onSave }) {
  const other = useBox(request.other_carriers, (value) => onSave({ other_carriers: value }));
  const due = useBox(request.due_date, (value) => onSave({ due_date: value }));
  const notes = useBox(request.notes, (value) => onSave({ notes: value }));
  return (
    <>
      <div className="bnf-rfp-fields">
        <label>
          <span>Other carriers</span>
          <input type="text" placeholder="Anyone not listed above" maxLength={limits?.other_carriers} {...other} />
        </label>
        <label>
          <span>Quotes due back</span>
          <input type="date" {...due} />
        </label>
      </div>
      <label className="bnf-rfp-notes">
        <span>Notes for the carriers</span>
        <textarea
          rows={3}
          maxLength={limits?.notes}
          placeholder="Anything the numbers don't say — a nuance, a deadline, a plan design to match."
          {...notes}
        />
      </label>
    </>
  );
}
