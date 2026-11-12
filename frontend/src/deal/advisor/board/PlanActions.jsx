import PlanMenu from '../PlanMenu';

/*
 * A plan's ⋯ menu on the board: 2V's plan actions (F134) kept until their slices place them (the Proposal grid's plan
 * menu, the booking): Create renewal, Duplicate (with its rates, F81), Change role & links…, Mark sold / Un-sell and
 * Delete… (a soft delete with Undo, F60; the board asks first). Every action is the board's (`actions`), which toasts
 * and offers Undo.
 */
export default function PlanActions({ plan, actions, plans }) {
  const hasRenewal = plans.some((p) => p.role === 'renewal' && p.renews_id === plan.id);
  const items = [
    plan.role === 'current' &&
      !hasRenewal && { key: 'renewal', label: 'Create renewal', onSelect: () => actions.createRenewal(plan) },
    { key: 'copy', label: 'Duplicate', onSelect: () => actions.copy(plan) },
    { key: 'links', label: 'Change role & links…', onSelect: () => actions.editLinks(plan) },
    { key: 'sold', label: plan.sold ? 'Un-sell' : 'Mark sold', onSelect: () => actions.setSold(plan, !plan.sold) },
    { key: 'delete', label: 'Delete…', danger: true, onSelect: () => actions.remove([plan.id]) },
  ].filter(Boolean);
  return <PlanMenu label={`Actions for ${plan.carrier} — ${plan.name}`} items={items} />;
}
