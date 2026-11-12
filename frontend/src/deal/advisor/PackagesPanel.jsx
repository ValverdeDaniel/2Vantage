import { useId, useState } from 'react';
import { errorText, fieldErrors } from '../../lib/errors';
import { formatMoney } from '../../lib/format';
import Button from '../../ui/Button';
import Field from '../../ui/Field';
import Modal from '../../ui/Modal';
import TextInput from '../../ui/TextInput';
import { useToast } from '../../ui/useToast';
import { changeText } from './display';

function PackageDialog({ onClose, comparison, existing, create, update }) {
  const [name, setName] = useState(existing?.name ?? '');
  const [ids, setIds] = useState(new Set(existing?.plan_ids ?? []));
  const mutation = existing ? update : create;
  const errors = fieldErrors(mutation.error);
  const groupId = useId();

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
          <Button size="sm" onClick={onClose}>
            Cancel
          </Button>
          <Button size="sm" type="submit" variant="primary" busy={mutation.isPending}>
            Save package
          </Button>
        </>
      }
    >
      <Field label="Name" required error={errors.name} help="e.g. UHC — consolidated, Cigna with HDHP">
        <TextInput value={name} onChange={(event) => setName(event.target.value)} />
      </Field>
      <div role="group" aria-labelledby={groupId} className="bnf-build-panel">
        <div id={groupId} className="bnf-packet-group">
          Plans the client would buy together
        </div>
        {comparison.plans.map((plan) => (
          <label key={plan.id} className="bnf-output-check">
            <input type="checkbox" checked={ids.has(plan.id)} onChange={() => toggle(plan.id)} /> {plan.carrier}{' '}
            {plan.name} <span className="bb-account-sub">({plan.role})</span>
          </label>
        ))}
      </div>
      {errors.plan_ids && (
        <em role="alert" className="bnf-saved-error">
          {errors.plan_ids}
        </em>
      )}
    </Modal>
  );
}

/**
 * Packages below the grid (plan.md §5.5): a total and change, or the reason in words. 2V's ＋ Package has no old
 * twin (§8.15's gap); it sits in an old panel with the builder's packet rows.
 */
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
    <section className="bb-panel bnf-build-panel" aria-labelledby="packages-title">
      <div className="bnf-bcard-head">
        <h3 id="packages-title" className="bb-panel-title">
          Packages
        </h3>
        <span className="bnf-bcard-mark">
          <Button size="sm" onClick={() => setEditing('new')}>
            ＋ Package
          </Button>
        </span>
      </div>
      {!comparison.packages.length && (
        <div className="bnf-packet-note">No packages yet. Current plans make the first one.</div>
      )}
      <div>
        {comparison.packages.map((pkg) => {
          const member = members[pkg.key];
          return (
            <div key={pkg.key} className="bnf-packet-row">
              <span className="bnf-packet-tick bnf-packet-label">{pkg.label}</span>
              <span className="bnf-packet-hint">
                {pkg.plan_ids.map((id) => byId[id]?.name).filter(Boolean).join(' + ') || 'no plans'}
              </span>
              <span className="bnf-pk-figures">
                {pkg.annual != null && <span className="bb-mono">{formatMoney(pkg.annual)}/yr</span>}
                {pkg.change && (
                  <span className="bnf-delta">
                    {changeText(pkg.change)}
                    {pkg.key === 'renewal' ? ' average' : ''}
                  </span>
                )}
                {pkg.reason && <span className="bnf-pk-why">⚠ {pkg.reason}</span>}
              </span>
              {member && (
                <>
                  <Button size="sm" onClick={() => setEditing(member)}>
                    Edit
                  </Button>
                  <Button size="sm" onClick={() => onDelete(member)}>
                    Delete
                  </Button>
                </>
              )}
            </div>
          );
        })}
      </div>
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
