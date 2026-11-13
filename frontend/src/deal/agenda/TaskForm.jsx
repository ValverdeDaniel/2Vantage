import { useState } from 'react';
import { useUsers } from '../../api/deals';
import Button from '../../ui/Button';

/*
 * A task added by hand (I27, I33): the old "Add a task" form (891f1b3 `shared/DealAgendaTab.jsx`: title, date, For,
 * Add; `bnf-event-form bnf-ag-addform`), its date starting on the agency's today and its For choice remembered after
 * each add. Editing opens the same form on a task, with its note (I33, new). People come from `GET users/` (I29).
 */
export default function TaskForm({ today, task, busy, onSave, onCancel, remembered = '' }) {
  const users = useUsers().data || [];
  const empty = { title: '', due: today, assigned_to: remembered, note: '' };
  const [draft, setDraft] = useState(
    task
      ? { title: task.title, due: task.due, assigned_to: task.assigned_to?.id ?? '', note: task.note || '' }
      : empty,
  );
  const set = (key) => (event) => setDraft({ ...draft, [key]: event.target.value });

  async function submit(event) {
    event.preventDefault();
    if (!draft.title.trim() || !draft.due) return;
    const body = { title: draft.title, due: draft.due, assigned_to: draft.assigned_to || null };
    const saved = await onSave(task ? { ...body, note: draft.note } : body);
    if (saved && !task) setDraft({ ...empty, assigned_to: draft.assigned_to });
  }

  return (
    <form className="bnf-event-form bnf-ag-addform" onSubmit={submit}>
      <input
        className="bnf-event-title"
        placeholder="Add a task… (“send the renewal to HR”)"
        value={draft.title}
        onChange={set('title')}
        aria-label="Task"
      />
      <input type="date" value={draft.due} onChange={set('due')} aria-label="Due" />
      <select value={draft.assigned_to} onChange={set('assigned_to')} aria-label="For">
        <option value="">For the deal&apos;s owner</option>
        {users.map((person) => (
          <option key={person.id} value={person.id}>
            For {person.name}
          </option>
        ))}
      </select>
      {task && (
        <input className="bnf-ag-note" placeholder="Note (optional)" value={draft.note} onChange={set('note')}
          aria-label="Note" />
      )}
      <Button variant="primary" size="sm" type="submit" busy={busy}>
        {task ? (busy ? 'Saving…' : 'Save') : busy ? 'Adding…' : 'Add'}
      </Button>
      {onCancel && (
        <Button size="sm" onClick={onCancel}>
          Cancel
        </Button>
      )}
    </form>
  );
}
