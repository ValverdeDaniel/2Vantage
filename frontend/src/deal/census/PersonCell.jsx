import AddDependentMenu from './AddDependentMenu';
import { depLabel, personName } from './rosterModel';

/*
 * The roster's frozen Person column (plan.md §8.10; C2, C7; the old CensusGrid at 891f1b3): an employee's Emp ID
 * beside "＋ Dep", or a dependent's "↳ Spouse". Locked means locked: outside ✎ Edit "＋ Dep" still shows, greyed, so
 * it can be found, and × (remove the person, an employee's dependents too) appears only in Edit, on hover.
 */
export default function PersonCell({ member, editing, picking, relationships, onAddDependent, onRemove }) {
  const employee = member.kind === 'employee';
  const name = personName(member) || member.values?.ext_emp_id || 'this employee';
  return (
    <div className="bb-loc-col bb-loc-cell bnf-person-col bnf-census-person">
      {employee ? (
        <span className="bb-mono bnf-census-empid" title={member.values?.ext_emp_id || undefined}>
          {member.values?.ext_emp_id || '—'}
        </span>
      ) : (
        <span className="bnf-dep-marker" title={member.values?.relationship || 'Dependent: no relationship yet'}>
          ↳ {depLabel(member)}
        </span>
      )}
      {!picking && (
        <span className="bnf-row-actions">
          {employee &&
            (editing ? (
              <AddDependentMenu name={name} choices={relationships} onPick={(rel) => onAddDependent(member, rel)} />
            ) : (
              <span className="bnf-locked-hint" title="Press ✎ Edit to add a dependent">
                <button type="button" className="bnf-dep-add" disabled>
                  ＋ Dep
                </button>
              </span>
            ))}
          {editing && (
            <button
              type="button"
              className="bnf-row-btn bnf-row-delete"
              title={employee ? 'Remove employee + dependents' : 'Remove dependent'}
              aria-label={employee ? `Remove ${name} and their dependents` : 'Remove this dependent'}
              onClick={() => onRemove(member)}
            >
              ×
            </button>
          )}
        </span>
      )}
    </div>
  );
}
