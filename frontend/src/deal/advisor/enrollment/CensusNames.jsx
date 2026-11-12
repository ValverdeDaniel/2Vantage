/*
 * The census's plan names, matched to the line's current plans (plan.md §5.5 step 4; F90, C41): one row per plan
 * text an enrolled employee names, with how many and the current plan it means. Exact names and plan numbers are
 * matched automatically; a person picks the rest once, and the census prices each current plan from its own members
 * once every text is matched. Saved with the card (`census_names`).
 */
const HOW = { name: 'matched by name', number: 'matched by plan number', hand: 'matched by hand' };

export default function CensusNames({ texts, currents, choice, onChoose }) {
  const open = texts.filter((row) => !choice[row.text]).length;
  return (
    <div className="bnf-pv-body">
      <span className="bnf-pv-picklabel">
        Census plan names{' '}
        <span className="bnf-pc-note">
          {open
            ? `${open} not matched yet: the census prices these current plans once every name is matched.`
            : 'Every name is matched: the census can price each current plan from its own members.'}
        </span>
      </span>
      <table className="bnf-pc-table">
        <thead>
          <tr>
            <th scope="col">On the census</th>
            <th scope="col">Employees</th>
            <th scope="col">Means</th>
          </tr>
        </thead>
        <tbody>
          {texts.map((row) => (
            <tr key={row.text}>
              <th scope="row">
                {row.text || '(no plan named)'}
                {row.how && choice[row.text] === row.plan_id && <span className="bnf-pc-note">{HOW[row.how]}</span>}
              </th>
              <td className="bnf-pc-total">{row.enrolled}</td>
              <td>
                <select
                  className="filter-select"
                  aria-label={`What "${row.text}" means`}
                  value={choice[row.text] ?? ''}
                  onChange={(event) => onChoose(row.text, event.target.value ? Number(event.target.value) : '')}
                >
                  <option value="">Not matched</option>
                  {currents.map((plan) => (
                    <option key={plan.id} value={plan.id}>
                      {plan.carrier} {plan.name}
                    </option>
                  ))}
                </select>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
