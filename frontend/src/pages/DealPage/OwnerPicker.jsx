import { useId } from 'react';
import { useUpdateDeal, useUsers } from '../../api/deals';
import SaveStatus from '../../ui/SaveStatus';
import Select from '../../ui/Select';
import styles from './HeaderFields.module.css';

/** "Owner: Dana Lee ▾" — saves on change. A deactivated owner stays listed until someone else is chosen. */
export default function OwnerPicker({ deal }) {
  const id = useId();
  const users = useUsers();
  const update = useUpdateDeal(deal.id);
  const people = [...(users.data || [])];
  if (deal.owner && !people.some((person) => person.id === deal.owner.id)) people.unshift(deal.owner);

  return (
    <span className={styles.fact}>
      <label htmlFor={id} className={styles.label}>
        Owner:
      </label>
      <Select
        id={id}
        size="sm"
        value={deal.owner ? String(deal.owner.id) : ''}
        placeholder="Unassigned"
        options={people.map((person) => ({ value: String(person.id), label: person.name }))}
        onChange={(event) => update.mutate({ owner_id: event.target.value ? Number(event.target.value) : null })}
      />
      <SaveStatus mutation={update} />
    </span>
  );
}
