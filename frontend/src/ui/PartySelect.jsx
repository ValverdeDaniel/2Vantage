/**
 * Pick who holds a share (H11, H12, H116; 891f1b3 `commissions/PartySelect.jsx`, its words and classes): the people
 * the server listed (a producer with a login and no Party yet is listed too, keyed `u<user id>`; a Party `p<id>`),
 * grouped by kind when more than one kind is offered. `requireAppointed` greys out producers who are neither
 * appointed nor able to sign in: the primary must be on the AOR letter. People used on other rows are left out.
 *   people: [{key, name, kind, appointed, login}] · value: a key · onChange(key | null) · kinds: [kind] · groups: {kind:
 *   label} (meta `commission.kind_groups`) · excludeKeys · emptyLabel
 */
export default function PartySelect({
  people = [],
  value,
  onChange,
  kinds = null,
  groups = {},
  requireAppointed = false,
  excludeKeys = [],
  emptyLabel = 'Pick a person…',
  disabled = false,
  label = 'Person',
  className = 'bnf-intake-input',
}) {
  const usable = people.filter(
    (person) => (!kinds || kinds.includes(person.kind)) && (!excludeKeys.includes(person.key) || person.key === value),
  );
  const order = Object.keys(groups);
  const byKind = order
    .map((kind) => ({ kind, items: usable.filter((person) => person.kind === kind) }))
    .filter((group) => group.items.length);
  const notAppointed = (person) => requireAppointed && person.kind === 'producer' && !person.appointed && !person.login;
  const option = (person) => (
    <option key={person.key} value={person.key} disabled={notAppointed(person)}>
      {person.name}
      {notAppointed(person) ? ' (not appointed)' : ''}
    </option>
  );
  return (
    <select
      className={className}
      value={value || ''}
      disabled={disabled}
      aria-label={label}
      onChange={(event) => onChange(event.target.value || null)}
    >
      <option value="">{emptyLabel}</option>
      {byKind.length <= 1
        ? usable.map(option)
        : byKind.map((group) => (
            <optgroup key={group.kind} label={groups[group.kind]}>
              {group.items.map(option)}
            </optgroup>
          ))}
    </select>
  );
}
