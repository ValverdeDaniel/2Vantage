import { useState } from 'react';
import { formErrorText } from '../../lib/errors';
import Button from '../../ui/Button';
import Modal from '../../ui/Modal';
import MultiSelect from '../../ui/MultiSelect';
import { useToast } from '../../ui/useToast';
import { enrollmentKeys } from './display';
import styles from './AdvisorTab.module.css';

const LABELS = { EE: 'EE', ES: 'ES', EC: 'EC', FAM: 'FAM', volume: 'Volume ($)', lives: 'Lives' };

/**
 * Typed enrollment for the line's plans (plan.md §5.5, §8.11). Inputs follow the line's rate basis. Plans bought
 * together in place of one plan each get their share of its people here. Saves all rows at once.
 */
export default function EnrollmentCard({ open, onClose, comparison, preselect, save }) {
  return open ? <Card onClose={onClose} comparison={comparison} preselect={preselect} save={save} /> : null;
}

function initialRows(plans, keys) {
  return Object.fromEntries(
    plans.map((plan) => [
      plan.id,
      {
        on: plan.enrollment_on,
        values: Object.fromEntries(keys.map((key) => [key, String(plan.enrollment?.[key] ?? '')])),
      },
    ]),
  );
}

function Card({ onClose, comparison, preselect, save }) {
  const toast = useToast();
  const keys = enrollmentKeys(comparison.rate_basis);
  const plans = comparison.plans;
  const defaults = preselect?.length
    ? preselect
    : plans.filter((p) => p.role === 'current' || p.enrollment_on).map((p) => p.id);
  const [selected, setSelected] = useState(defaults.map(String));
  const [rows, setRows] = useState(() => initialRows(plans, keys));
  const chosen = plans.filter((plan) => selected.includes(String(plan.id)));
  // A plan created a moment ago may arrive after the first render: give it an empty row.
  const rowOf = (plan) =>
    rows[plan.id] ?? { on: true, values: Object.fromEntries(keys.map((key) => [key, ''])) };

  function setValue(planId, key, value) {
    setRows((prev) => {
      const row = prev[planId] ?? rowOf({ id: planId });
      return { ...prev, [planId]: { ...row, values: { ...row.values, [key]: value } } };
    });
  }

  function copyFirst() {
    const first = chosen[0];
    if (!first) return;
    setRows((prev) => {
      const next = { ...prev };
      chosen.slice(1).forEach((plan) => {
        next[plan.id] = { ...rowOf(plan), values: { ...rowOf(first).values } };
      });
      return next;
    });
  }

  async function submit() {
    const body = chosen.map((plan) => ({
      id: plan.id,
      on: rowOf(plan).on,
      enrollment: Object.fromEntries(keys.map((key) => [key, rowOf(plan).values[key] || 0])),
    }));
    await save.mutateAsync(body);
    toast.success('Enrollment saved');
    onClose();
  }

  return (
    <Modal
      open
      size="lg"
      title="Enrollment"
      onClose={onClose}
      onSubmit={() => submit().catch(() => {})}
      footer={
        <>
          <Button onClick={copyFirst} disabled={chosen.length < 2}>
            Copy first row to all
          </Button>
          <Button onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="primary" busy={save.isPending} disabled={!chosen.length}>
            Save
          </Button>
        </>
      }
    >
      <MultiSelect
        label="Plans"
        value={selected}
        onChange={setSelected}
        options={plans.map((plan) => ({ value: String(plan.id), label: `${plan.carrier} ${plan.name}` }))}
        placeholder="Add a plan…"
      />
      <p className={styles.hint}>
        Renewals and alternates use the enrollment of the plan they replace unless they have their own. Plans bought
        together in place of one plan: give each its share of that plan&apos;s people.
      </p>
      <table className={styles.enrollment}>
        <thead>
          <tr>
            <th scope="col">Plan</th>
            {keys.map((key) => (
              <th scope="col" key={key}>
                {LABELS[key]}
              </th>
            ))}
            <th scope="col">On</th>
          </tr>
        </thead>
        <tbody>
          {chosen.map((plan) => (
            <tr key={plan.id}>
              <th scope="row">
                {plan.carrier} {plan.name}
              </th>
              {keys.map((key) => (
                <td key={key}>
                  <input
                    className={styles.count}
                    inputMode="numeric"
                    aria-label={`${plan.name} ${LABELS[key]}`}
                    value={rowOf(plan).values[key]}
                    onChange={(event) => setValue(plan.id, key, event.target.value)}
                  />
                </td>
              ))}
              <td>
                <input
                  type="checkbox"
                  aria-label={`Use ${plan.name}'s typed enrollment`}
                  checked={rowOf(plan).on}
                  onChange={(event) =>
                    setRows((prev) => ({ ...prev, [plan.id]: { ...rowOf(plan), on: event.target.checked } }))
                  }
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {save.error && <p role="alert">{formErrorText(save.error)}</p>}
    </Modal>
  );
}
