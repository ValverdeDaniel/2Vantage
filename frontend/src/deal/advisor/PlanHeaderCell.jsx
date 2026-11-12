import { useState } from 'react';
import { errorText } from '../../lib/errors';
import ConfirmDialog from '../../ui/ConfirmDialog';
import cx from '../../ui/cx';
import { useToast } from '../../ui/useToast';
import { roleText } from './display';
import PlanMenu from './PlanMenu';

// The old column chips (ComparisonGrid.jsx at 891f1b3): CURRENT blue, RENEWAL, and the new-plan tint for alternates.
const ROLE_CHIP = { current: 'bnf-chip-current', renewal: 'bnf-chip-renewal', alternate: 'bnf-chip-new' };

function InlineText({ value, label, onSave, className }) {
  const [draft, setDraft] = useState(null);
  return (
    <input
      aria-label={label}
      title={value}
      className={cx('bb-cell-input', className)}
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

/** The head of one plan column (plan.md §8.14; 2V's simplified Advisor, F134), in the old grid's column head. */
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
    { key: 'delete', label: 'Delete…', danger: true, onSelect: () => setConfirmDelete(true) },
  ].filter(Boolean);

  const save = (changes) => run(actions.update.mutateAsync({ planId: plan.id, changes }));
  const role = roleText(plan, byId);
  const moving = actions.order.isPending;

  return (
    <th
      scope="col"
      className={cx(plan.role === 'current' && 'bnf-plan-col-current', plan.sold && 'bnf-plan-col-sold')}
    >
      <div className="bnf-plan-head">
        <div>
          <span className={cx('bnf-plan-chip', ROLE_CHIP[plan.role])} title={role}>
            {role}
          </span>{' '}
          {plan.sold && <span className="bnf-plan-chip bnf-chip-sold">SOLD ✓</span>}
          <InlineText
            value={plan.carrier}
            label="Carrier"
            className="bnf-plan-carrier"
            onSave={(carrier) => save({ carrier })}
          />
          <InlineText value={plan.name} label="Plan name" className="bnf-plan-name" onSave={(name) => save({ name })} />
        </div>
        <span className="bnf-order-arrows">
          <button
            type="button"
            className="bnf-build-order-btn"
            disabled={moving || isFirst}
            aria-label={`Move ${plan.name} left`}
            title="Move left"
            onClick={() => actions.move(plan, -1)}
          >
            ◀
          </button>
          <button
            type="button"
            className="bnf-build-order-btn"
            disabled={moving || isLast}
            aria-label={`Move ${plan.name} right`}
            title="Move right"
            onClick={() => actions.move(plan, 1)}
          >
            ▶
          </button>
          <PlanMenu label={`Actions for ${plan.name}`} items={items} />
        </span>
      </div>
      <div className="bnf-present-checks">
        <button
          type="button"
          className={cx('bnf-star-btn', plan.starred && 'active')}
          aria-pressed={plan.starred}
          aria-label="Star"
          title={plan.starred ? 'Starred: shortlisted for the proposal' : 'Star to shortlist for the proposal'}
          onClick={() => run(actions.star.mutateAsync({ planIds: [plan.id], starred: !plan.starred }))}
        >
          {plan.starred ? '★' : '☆'}
        </button>
        {plan.role !== 'current' && (
          <label className="bnf-filter-check">
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
        <label className="bnf-filter-check">
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
