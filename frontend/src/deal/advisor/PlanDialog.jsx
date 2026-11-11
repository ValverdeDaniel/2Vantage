import { useState } from 'react';
import { fieldErrors, formErrorText } from '../../lib/errors';
import Button from '../../ui/Button';
import Field from '../../ui/Field';
import Modal from '../../ui/Modal';
import MultiSelect from '../../ui/MultiSelect';
import Select from '../../ui/Select';
import TextInput from '../../ui/TextInput';

const ROLES = [
  { value: 'current', label: 'Current — in force today' },
  { value: 'renewal', label: "Renewal — the current carrier's new rates" },
  { value: 'alternate', label: 'Alternate — a competing plan' },
];

/**
 * "+ Plan" (plan is null) or "Change role & links" (plan given) — plan.md §8.11.
 * An alternate replaces none, one or several current plans (several = a consolidation, none = an added plan). When
 * a second alternate takes the place of the same current plan, the member says whether it is an option (it carries
 * that plan's whole enrollment) or bought together (onBoughtTogether opens the Enrollment card to split the people).
 */
export default function PlanDialog({ open, onClose, line, plan, plans, create, update, onBoughtTogether }) {
  return open ? (
    <PlanForm
      onClose={onClose}
      line={line}
      plan={plan}
      plans={plans}
      create={create}
      update={update}
      onBoughtTogether={onBoughtTogether}
    />
  ) : null;
}

function PlanForm({ onClose, line, plan, plans, create, update, onBoughtTogether }) {
  const current = plans.filter((p) => p.role === 'current' && p.id !== plan?.id);
  const [role, setRole] = useState(plan?.role ?? (current.length ? 'alternate' : 'current'));
  const [renews, setRenews] = useState(String(plan?.renews_id ?? ''));
  const [replaces, setReplaces] = useState((plan?.replaces_ids ?? []).map(String));
  const [carrier, setCarrier] = useState(plan?.carrier ?? '');
  const [name, setName] = useState(plan?.name ?? '');
  const [number, setNumber] = useState(plan?.plan_number ?? '');
  const [kind, setKind] = useState('option');
  const mutation = plan ? update : create;
  const errors = fieldErrors(mutation.error);

  const alreadyReplaced = replaces.filter((id) =>
    plans.some((p) => p.id !== plan?.id && p.role === 'alternate' && (p.replaces_ids ?? []).map(String).includes(id)),
  );
  const askKind = !plan && role === 'alternate' && replaces.length === 1 && alreadyReplaced.length === 1;

  async function submit() {
    const links = {
      renews_id: role === 'renewal' ? Number(renews) || null : null,
      replaces_ids: role === 'alternate' ? replaces.map(Number) : [],
    };
    if (plan) {
      await update.mutateAsync({ planId: plan.id, changes: { role, ...links } });
      onClose();
      return;
    }
    const created = await create.mutateAsync({ line, role, carrier, name, plan_number: number, ...links });
    onClose();
    if (askKind && kind === 'together') {
      const partner = plans.find(
        (p) => p.role === 'alternate' && (p.replaces_ids ?? []).map(String).includes(replaces[0]),
      );
      onBoughtTogether([created.id, partner?.id].filter(Boolean));
    }
  }

  return (
    <Modal
      open
      onClose={onClose}
      title={plan ? `Role and links — ${plan.name}` : 'Add a plan'}
      onSubmit={() => submit().catch(() => {})}
      footer={
        <>
          <Button onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="primary" busy={mutation.isPending}>
            {plan ? 'Save' : 'Add plan'}
          </Button>
        </>
      }
    >
      <Field label="Role">
        <Select value={role} onChange={(event) => setRole(event.target.value)} options={ROLES} />
      </Field>
      {role === 'renewal' && (
        <Field label="Renews" required error={errors.renews_id}>
          <Select
            value={renews}
            placeholder="Choose the current plan"
            onChange={(event) => setRenews(event.target.value)}
            options={current.map((p) => ({ value: String(p.id), label: `${p.carrier} ${p.name}` }))}
          />
        </Field>
      )}
      {role === 'alternate' && (
        <Field
          label="Replaces"
          help="One plan: in its place. Several: a consolidation. None: a plan added beside the current plans."
          error={errors.links}
        >
          <MultiSelect
            value={replaces}
            onChange={setReplaces}
            placeholder="Search current plans…"
            emptyText={current.length ? 'None chosen: a plan added beside them.' : 'No current plans on this line yet.'}
            options={current.map((p) => ({ value: String(p.id), label: `${p.carrier} ${p.name}` }))}
          />
        </Field>
      )}
      {askKind && (
        <fieldset>
          <legend>Another plan already replaces {current.find((p) => String(p.id) === replaces[0])?.name}.</legend>
          <label>
            <input type="radio" checked={kind === 'option'} onChange={() => setKind('option')} /> An option — the
            client picks one; it carries the plan&apos;s whole enrollment
          </label>
          <br />
          <label>
            <input type="radio" checked={kind === 'together'} onChange={() => setKind('together')} /> Bought together
            — offered side by side; split the people in the Enrollment card next
          </label>
        </fieldset>
      )}
      {!plan && (
        <>
          <Field label="Carrier" required error={errors.carrier}>
            <TextInput value={carrier} onChange={(event) => setCarrier(event.target.value)} />
          </Field>
          <Field label="Plan name" required error={errors.name}>
            <TextInput value={name} onChange={(event) => setName(event.target.value)} />
          </Field>
          <Field label="Plan number">
            <TextInput value={number} onChange={(event) => setNumber(event.target.value)} />
          </Field>
        </>
      )}
      {mutation.error && (
        <p role="alert">{formErrorText(mutation.error, ['carrier', 'name', 'renews_id', 'links'])}</p>
      )}
    </Modal>
  );
}
