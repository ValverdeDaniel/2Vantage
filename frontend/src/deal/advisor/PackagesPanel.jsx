import { useState } from 'react';
import { errorText, fieldErrors } from '../../lib/errors';
import { formatMoney } from '../../lib/format';
import Button from '../../ui/Button';
import Field from '../../ui/Field';
import Modal from '../../ui/Modal';
import TextInput from '../../ui/TextInput';
import { useToast } from '../../ui/useToast';
import styles from './AdvisorTab.module.css';
import { changeText } from './display';

function PackageDialog({ onClose, comparison, existing, create, update }) {
  const [name, setName] = useState(existing?.name ?? '');
  const [ids, setIds] = useState(new Set(existing?.plan_ids ?? []));
  const mutation = existing ? update : create;
  const errors = fieldErrors(mutation.error);

  function toggle(id) {
    setIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function submit() {
    const body = { name, plan_ids: [...ids] };
    if (existing) await update.mutateAsync({ packageId: existing.id, changes: body });
    else await create.mutateAsync({ line: comparison.line, ...body });
    onClose();
  }

  return (
    <Modal
      open
      title={existing ? `Edit ${existing.name}` : 'Build a package'}
      onClose={onClose}
      onSubmit={() => submit().catch(() => {})}
      footer={
        <>
          <Button onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="primary" busy={mutation.isPending}>
            Save package
          </Button>
        </>
      }
    >
      <Field label="Name" required error={errors.name} help="e.g. UHC — consolidated, Cigna with HDHP">
        <TextInput value={name} onChange={(event) => setName(event.target.value)} />
      </Field>
      <fieldset className={styles.planChecks}>
        <legend>Plans the client would buy together</legend>
        {comparison.plans.map((plan) => (
          <label key={plan.id}>
            <input type="checkbox" checked={ids.has(plan.id)} onChange={() => toggle(plan.id)} /> {plan.carrier}{' '}
            {plan.name} <span className={styles.muted}>({plan.role})</span>
          </label>
        ))}
      </fieldset>
      {errors.plan_ids && <p role="alert">{errors.plan_ids}</p>}
    </Modal>
  );
}

/** Packages below the grid (plan.md §5.5): a total and change, or the reason in words. */
export default function PackagesPanel({ comparison, create, update, remove }) {
  const toast = useToast();
  const [editing, setEditing] = useState(null);
  const byId = Object.fromEntries(comparison.plans.map((plan) => [plan.id, plan]));
  const members = Object.fromEntries(comparison.member_packages.map((p) => [`package:${p.id}`, p]));

  async function onDelete(member) {
    try {
      await remove.mutateAsync(member.id);
      toast.success(`Deleted ${member.name}`);
    } catch (error) {
      toast.error(errorText(error));
    }
  }

  return (
    <section className={styles.packages} aria-labelledby="packages-title">
      <div className={styles.packagesHead}>
        <h3 id="packages-title">Packages</h3>
        <Button size="sm" onClick={() => setEditing('new')}>
          + Package
        </Button>
      </div>
      {!comparison.packages.length && (
        <p className={styles.muted}>No packages yet. Current plans make the first one.</p>
      )}
      <ul className={styles.packageList}>
        {comparison.packages.map((pkg) => {
          const member = members[pkg.key];
          return (
            <li key={pkg.key}>
              <div>
                <strong>{pkg.label}</strong>{' '}
                <span className={styles.muted}>
                  {pkg.plan_ids.map((id) => byId[id]?.name).filter(Boolean).join(' + ') || 'no plans'}
                </span>
              </div>
              <div className={styles.packageFigures}>
                {pkg.annual != null && <span>{formatMoney(pkg.annual)}/yr</span>}
                {pkg.change && (
                  <span>
                    {changeText(pkg.change)}
                    {pkg.key === 'renewal' ? ' average' : ''}
                  </span>
                )}
                {pkg.reason && (
                  <span className={styles.reason}>
                    <span aria-hidden="true">⚠ </span>
                    {pkg.reason}
                  </span>
                )}
                {member && (
                  <>
                    <Button size="sm" variant="ghost" onClick={() => setEditing(member)}>
                      Edit
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => onDelete(member)}>
                      Delete
                    </Button>
                  </>
                )}
              </div>
            </li>
          );
        })}
      </ul>
      {editing && (
        <PackageDialog
          onClose={() => setEditing(null)}
          comparison={comparison}
          existing={editing === 'new' ? null : editing}
          create={create}
          update={update}
        />
      )}
    </section>
  );
}
