import { useState } from 'react';
import AddPersonForm from './AddPersonForm';
import CellInput from './CellInput';
import ConflictNote from './ConflictNote';
import FieldHelp from './FieldHelp';
import { cellRef, groupFields } from './portalModel';

/*
 * Employee details (plan.md §8.20; L88, L90; C35). Ported from old Vantage 891f1b3 `BenefitsClientPortal.jsx`: a card
 * per person asked, their fields under the employer's headings with the star, the help and the conflict note; "＋ Add
 * a dependent of …" under an employee, and "Someone missing?" with "＋ Add an employee". A person they added shows
 * at once with what we ask of them, and waits for a person at the agency (Ch. 12).
 *
 * bind: the answers (PortalForm); adder: {open, relationships, left} or null; onAdd(person) → a promise.
 */
function Person({ person, bind, adding, setAdding, adder, onAdd }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const dependentForm = adding?.employeeId === person.id;

  async function save(draft) {
    setBusy(true);
    setError('');
    try {
      await onAdd({ kind: 'dependent', employee_id: person.id, ...draft });
      setAdding(null);
    } catch (failure) {
      setError(failure?.message || 'Could not add that person — please try again.');
    }
    setBusy(false);
  }

  return (
    <div className={`bb-portal-card ${person.kind === 'dependent' ? 'bnf-portal-dependent' : ''}`}>
      <div className="bb-panel-title">{person.title}</div>
      <div className="bb-panel-sub">
        {person.kind === 'dependent' ? 'Dependent' : 'Employee'}
        {person.added ? ' · added by your team' : ''}
      </div>
      {groupFields(person.fields).map((group) => (
        <div key={group.key || 'other'}>
          {group.label && <div className="bnf-portal-group-title">{group.label}</div>}
          <div className="bb-portal-fields">
            {group.fields.map((field) => {
              const ref = cellRef(person.id, field.column);
              return (
                <div key={field.column} className="bb-portal-field" data-ask-ref={ref}>
                  <label>
                    {field.label}
                    {field.required && (
                      <span className="bnf-qb-star" title="Needed to shop the market">
                        *
                      </span>
                    )}
                  </label>
                  <CellInput field={field} value={bind.values[ref]} disabled={bind.readOnly}
                             onChange={(value) => bind.set(ref, value)} />
                  <FieldHelp text={field.help} />
                  {field.by_colleague && <div className="bnf-portal-colleague">Updated by someone else on your team</div>}
                  {bind.errors[ref] && <div className="bnf-issue-line bb-rose">{bind.errors[ref]}</div>}
                  <ConflictNote conflict={bind.conflicts[ref]} onKeep={() => bind.keepTheirs(ref)}
                                onMine={() => bind.useMine(ref)} />
                </div>
              );
            })}
          </div>
        </div>
      ))}
      {person.kind === 'employee' && adder && adder.left > 0 && !bind.readOnly &&
        (dependentForm ? (
          <AddPersonForm dependentOf={person.title} relationships={adder.relationships} busy={busy} error={error}
                         onCancel={() => setAdding(null)} onSave={save} />
        ) : (
          <div className="bnf-portal-person-actions">
            <button type="button" className="bnf-override-link" onClick={() => setAdding({ employeeId: person.id })}>
              ＋ Add a dependent of {person.title}
            </button>
          </div>
        ))}
    </div>
  );
}

function SomeoneMissing({ adder, adding, setAdding, onAdd, readOnly }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function save(draft) {
    setBusy(true);
    setError('');
    try {
      await onAdd({ kind: 'employee', first_name: draft.first_name, last_name: draft.last_name });
      setAdding(null);
    } catch (failure) {
      setError(failure?.message || 'Could not add that person — please try again.');
    }
    setBusy(false);
  }
  return (
    <div className="bb-portal-card bnf-portal-addperson">
      {adding?.employee ? (
        <AddPersonForm relationships={adder.relationships} busy={busy} error={error} onCancel={() => setAdding(null)}
                       onSave={save} />
      ) : (
        <>
          <div className="bb-panel-title">Someone missing?</div>
          <div className="bb-panel-sub">
            Add anyone who should be on the roster and is not listed here — a new hire, or a dependent under their
            employee. We’ll ask for their details right away.
          </div>
          <button type="button" className="btn btn-secondary btn-sm" disabled={readOnly || adder.left <= 0}
                  onClick={() => setAdding({ employee: true })}>
            ＋ Add an employee
          </button>
        </>
      )}
    </div>
  );
}

export default function PeopleSection({ people, adder, bind, onAdd }) {
  const [adding, setAdding] = useState(null);
  return (
    <>
      {people.map((person, index) => (
        <div key={person.id} id={index === 0 ? 'bnf-sec-people' : undefined}>
          <Person person={person} bind={bind} adding={adding} setAdding={setAdding} adder={adder} onAdd={onAdd} />
        </div>
      ))}
      {adder && (
        <SomeoneMissing adder={adder} adding={adding} setAdding={setAdding} onAdd={onAdd} readOnly={bind.readOnly} />
      )}
    </>
  );
}
