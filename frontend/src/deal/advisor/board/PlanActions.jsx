import { useAttachSbc } from '../../claude';
import PlanMenu from '../PlanMenu';

/*
 * A plan's ⋯ menu on the board: 2V's plan actions (F134) kept until their slices place them (the Proposal grid's plan
 * menu, the booking): Create renewal, Duplicate (with its rates, F81), Change role & links…, Mark sold / Un-sell and
 * Delete… (a soft delete with Undo, F60; the board asks first); on a sold plan, Booked · view opens the booking
 * summary (H35; slice 49). Every action is the board's (`actions`), which toasts and offers Undo. "Attach SBC…"
 * (D38; slice 22) is Work with Claude's: a file for this plan's design, reviewed first.
 */
export default function PlanActions({ plan, actions, plans, line }) {
  const hasRenewal = plans.some((p) => p.role === 'renewal' && p.renews_id === plan.id);
  const sbc = useAttachSbc();
  const items = [
    plan.role === 'current' &&
      !hasRenewal && { key: 'renewal', label: 'Create renewal', onSelect: () => actions.createRenewal(plan) },
    { key: 'copy', label: 'Duplicate', onSelect: () => actions.copy(plan) },
    { key: 'links', label: 'Change role & links…', onSelect: () => actions.editLinks(plan) },
    sbc.can({ ...plan, line }) && { key: 'sbc', label: 'Attach SBC…', disabled: sbc.busy, onSelect: () => sbc.pick(plan) },
    { key: 'sold', label: plan.sold ? 'Un-sell' : 'Mark sold', onSelect: () => actions.setSold(plan, !plan.sold) },
    plan.sold && { key: 'booked', label: 'Booked · view', onSelect: () => actions.viewBooking() },
    { key: 'delete', label: 'Delete…', danger: true, onSelect: () => actions.remove([plan.id]) },
  ].filter(Boolean);
  return (
    <>
      {sbc.input}
      <PlanMenu label={`Actions for ${plan.carrier} — ${plan.name}`} items={items} />
    </>
  );
}
