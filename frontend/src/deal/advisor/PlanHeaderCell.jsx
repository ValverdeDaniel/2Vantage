import { useState } from 'react';
import { errorText } from '../../lib/errors';
import Badge from '../../ui/Badge';
import ConfirmDialog from '../../ui/ConfirmDialog';
import cx from '../../ui/cx';
import Menu from '../../ui/Menu';
import { useToast } from '../../ui/useToast';
import { roleText } from './display';
import styles from './PlanTable.module.css';

const ROLE_TONE = { current: 'neutral', renewal: 'info', alternate: 'success' };

function InlineText({ value, label, onSave, className }) {
  const [draft, setDraft] = useState(null);
  return (
    <input
      aria-label={label}
      title={value}
      className={cx(styles.headerInput, className)}
      value={draft ?? value}
      onFocus={() => setDraft(value)}
      onChange={(event) => setDraft(event.target.value)}
      onBlur={() => {
        const next = (draft ?? value).trim();
        setDraft(null);
        if (next && next !== value) onSave(next);
      }}
      onKeyDown={(event) => event.key === 'Enter' && event.currentTarget.blur()}
    />
  );
}

/** The sticky header of one plan column (plan.md §8.11). */
export default function PlanHeaderCell({ plan, byId, actions, isFirst, isLast }) {
  const toast = useToast();
  const [confirmDelete, setConfirmDelete] = useState(false);

  async function run(promise, success) {
    try {
      await promise;
      if (success) toast.success(success);
    } catch (error) {
      toast.error(errorText(error));
    }
  }

  const hasRenewal = Object.values(byId).some((p) => p.role === 'renewal' && p.renews_id === plan.id);
  const items = [
    plan.role === 'current' &&
      !hasRenewal && {
        key: 'renewal',
        label: 'Create renewal',
        onSelect: () => run(actions.createRenewal.mutateAsync(plan.id), 'Renewal created'),
      },
    {
      key: 'copy',
      label: 'Copy as alternate',
      onSelect: () => run(actions.copy.mutateAsync(plan.id), 'Copied as an alternate'),
    },
    { key: 'links', label: 'Change role & links…', onSelect: () => actions.editLinks(plan) },
    { key: 'left', label: 'Move left', disabled: isFirst, onSelect: () => actions.move(plan, -1) },
    { key: 'right', label: 'Move right', disabled: isLast, onSelect: () => actions.move(plan, 1) },
    { key: 'delete', label: 'Delete…', onSelect: () => setConfirmDelete(true) },
  ].filter(Boolean);

  const save = (changes) => run(actions.update.mutateAsync({ planId: plan.id, changes }));

  return (
    <th scope="col" className={cx(styles.planHead, styles[plan.role])}>
      <div className={styles.headTop}>
        <Badge tone={ROLE_TONE[plan.role]} className={styles.roleBadge} title={roleText(plan, byId)}>
          {roleText(plan, byId)}
        </Badge>
        <Menu label="⋯" ariaLabel={`Actions for ${plan.name}`} items={items} align="end" />
      </div>
      <InlineText value={plan.carrier} label="Carrier" onSave={(carrier) => save({ carrier })} />
      <InlineText
        value={plan.name}
        label="Plan name"
        className={styles.planName}
        onSave={(name) => save({ name })}
      />
      <div className={styles.toggles}>
        <button
          type="button"
          className={cx(styles.star, plan.starred && styles.on)}
          aria-pressed={plan.starred}
          title={plan.starred ? 'Starred: shortlisted for the proposal' : 'Star to shortlist for the proposal'}
          onClick={() => run(actions.star.mutateAsync({ planIds: [plan.id], starred: !plan.starred }))}
        >
          {plan.starred ? '★' : '☆'} <span className={styles.toggleText}>Star</span>
        </button>
        {plan.role !== 'current' && (
          <label className={styles.check}>
            <input
              type="checkbox"
              checked={plan.recommended}
              onChange={(event) =>
                run(actions.recommend.mutateAsync({ planId: plan.id, recommended: event.target.checked }))
              }
            />
            Rec.
          </label>
        )}
        <label className={styles.check}>
          <input
            type="checkbox"
            checked={plan.sold}
            onChange={(event) =>
              run(
                actions.sold.mutateAsync({ planId: plan.id, sold: event.target.checked }),
                event.target.checked ? `${plan.name} marked sold` : `${plan.name} un-sold`,
              )
            }
          />
          Sold
        </label>
      </div>
      <ConfirmDialog
        open={confirmDelete}
        title={`Delete ${plan.carrier} ${plan.name}?`}
        message={
          plan.role === 'current'
            ? 'Its renewal becomes an alternate, and alternates stop replacing it.'
            : 'This removes the plan and its values from the deal.'
        }
        confirmLabel="Delete"
        tone="danger"
        busy={actions.remove.isPending}
        onCancel={() => setConfirmDelete(false)}
        onConfirm={() =>
          run(actions.remove.mutateAsync(plan.id), 'Plan deleted').finally(() => setConfirmDelete(false))
        }
      />
    </th>
  );
}
