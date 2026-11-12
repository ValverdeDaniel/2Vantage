import { useState } from 'react';

/*
 * The two-name form behind "＋ Add an employee" / "＋ Add a dependent" (plan.md §8.20; L90). Ported from old Vantage
 * 891f1b3 `AddPersonForm`: names required (a nameless row could not be told apart later); a dependent's relationship
 * and birth date. The person waits whole until someone at the agency approves them (Ch. 12).
 */
export default function AddPersonForm({ dependentOf = null, relationships, busy, error, onCancel, onSave }) {
  const [draft, setDraft] = useState({ first_name: '', last_name: '', relationship: 'Spouse', dob: '' });
  const set = (key) => (event) => setDraft((current) => ({ ...current, [key]: event.target.value }));
  const ready = draft.first_name.trim() && draft.last_name.trim();
  return (
    <div className="bnf-portal-addform">
      <div className="bb-panel-sub">{dependentOf ? `Add a dependent of ${dependentOf}` : 'Add an employee'}</div>
      <div className="bb-portal-fields">
        <div className="bb-portal-field">
          <label htmlFor="add-first">First name</label>
          <input id="add-first" type="text" value={draft.first_name} onChange={set('first_name')} autoFocus />
        </div>
        <div className="bb-portal-field">
          <label htmlFor="add-last">Last name</label>
          <input id="add-last" type="text" value={draft.last_name} onChange={set('last_name')} />
        </div>
        {dependentOf && (
          <>
            <div className="bb-portal-field">
              <label htmlFor="add-relationship">Relationship</label>
              <select id="add-relationship" value={draft.relationship} onChange={set('relationship')}>
                {relationships.map((choice) => (
                  <option key={choice.value} value={choice.value}>
                    {choice.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="bb-portal-field">
              <label htmlFor="add-dob">Date of birth</label>
              <input id="add-dob" type="text" placeholder="MM/DD/YYYY" value={draft.dob} onChange={set('dob')} />
            </div>
          </>
        )}
      </div>
      {error && <div className="bnf-issue-line bb-rose">{error}</div>}
      <div className="bnf-portal-addform-actions">
        <button type="button" className="btn btn-secondary btn-sm" onClick={onCancel} disabled={busy}>
          Cancel
        </button>
        <button type="button" className="btn btn-primary btn-sm" disabled={!ready || busy} onClick={() => onSave(draft)}>
          {busy ? 'Adding…' : 'Add'}
        </button>
      </div>
    </div>
  );
}
