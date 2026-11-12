"""Marks on plans: stars, the shortlist, the recommendation and the sale (plan.md §5.4; F50, F51, F55, F123, H124).

- `star`: ★ puts a quote on the proposal, within `presented.room()` (16 columns a line, every presented column
  counted), refused with a sentence past it, under the Deal-row lock, so two people starring at once leave 16
  (Q.3 #8). A current plan takes no star. A star records its reason ("Hand-picked", or Rank's), who and when; a fresh
  star on an unlinked quote, on a line with two or more current plans, links it to the nearest current plan
  (`closeness`) in the same write (F51).
- `clear_shortlist`: one line's stars, one Activity row, revertible (F55).
- `set_recommended`: any plan, within `room()`; a recommended current plan is "Keep this plan" and takes no extra
  column, as in the old app (§5.4; OQ37, answered: "allow it as the old app did").
- `set_sold`: any number of plans a line (OQ12); a lost deal refuses it (H124). The sale moves the deal to Sold and
  calls `deals.services.sale_changed` in the same transaction; un-selling the last sold plan returns the deal to
  Proposal with its own Activity row (§5.1). Locks the Deal, then the Plan, then (in `sale_changed`) the Client.
"""

from django.db import transaction

from deals import activity, clock, lines, rules
from deals.services import advance, sale_changed

from .. import closeness, columns, presented, signals
from ..selectors.sales import client_has_sold
from . import locks
from .batch import Batch

HAND_PICKED = 'Hand-picked'
STAR_KEYS = (*columns.STAR, columns.REPLACES)
SALE_KEYS = ('plan.sold', 'plan.sold_at')


def _words(plan):
    return f'{plan.carrier} {plan.name}'


def _star_on(plan, user, reason, now):
    plan.starred, plan.star_reason = True, reason
    plan.starred_by_id, plan.starred_at = getattr(user, 'id', None), now


def _star_off(plan):
    plan.starred, plan.star_reason, plan.starred_by_id, plan.starred_at = False, '', None, None


def _star_line(user, deal, line_key, ids, starred, reason, now):
    """The plans of one line whose star changes, written; Refused past the line's room."""
    rows, data = locks.line(deal, line_key)
    targets = [rows[plan_id] for plan_id in ids]
    if not starred:
        batch = Batch(targets, STAR_KEYS)
        for plan in targets:
            if plan.starred:
                _star_off(plan)
        return batch.write()
    for plan in targets:
        if plan.role == 'current':
            raise activity.Refused(
                f'{_words(plan)} is a current plan — it is always on the proposal, so it takes no star.'
            )
    fresh = [plan for plan in targets if not plan.starred]
    adding = presented.added(data, [plan.id for plan in fresh if not plan.recommended])  # a pair counts once
    refusal = presented.refusal(data, lines.label(line_key), adding)
    if refusal:
        raise activity.Refused(refusal)
    batch = Batch(fresh, STAR_KEYS)
    field_set = lines.BY_KEY[line_key]['field_set']
    for plan in fresh:
        _star_on(plan, user, reason, now)
        if plan.role == 'alternate' and not plan.replaces_ids:
            nearest = closeness.nearest(data.by_id[plan.id], data.current, field_set)
            if nearest is not None:
                plan.replaces_ids = [nearest]
    return batch.write()


@transaction.atomic
def star(user, deal, plan_ids, starred, reason=HAND_PICKED):
    """Star or unstar plans (any lines of one deal). Returns (changed plans, Activity row or None)."""
    deal = locks.deal(deal.id)
    targets = locks.plans(deal, plan_ids)
    now = clock.now()
    changed, changes = [], []
    for line_key in sorted({plan.line for plan in targets}):
        ids = [plan.id for plan in targets if plan.line == line_key]
        line_changed, line_changes = _star_line(user, deal, line_key, ids, bool(starred), reason, now)
        changed += line_changed
        changes += line_changes
    if not changes:
        return [], None
    signals.changed(deal.id, [plan.line for plan in changed])
    summary, key = ('Starred', 'quotes:stars:on') if starred else ('Unstarred', 'quotes:stars:off')
    row = activity.record(deal, user, 'quotes', 'updated', summary, len(changed), key, 'plan', changes=changes)
    return changed, row


@transaction.atomic
def clear_shortlist(user, deal, line_key):
    """Every star on one line comes off (F55). Returns (changed plans, Activity row or None)."""
    deal = locks.deal(deal.id)
    rows, _data = locks.line(deal, line_key)
    starred = [plan for plan in rows.values() if plan.starred]
    batch = Batch(starred, STAR_KEYS)
    for plan in starred:
        _star_off(plan)
    changed, changes = batch.write()
    if not changes:
        return [], None
    signals.changed(deal.id, [line_key])
    summary = f'Cleared the {lines.label(line_key)} shortlist ({len(changed)} star{"s" if len(changed) != 1 else ""})'
    return changed, activity.record(deal, user, 'quotes', 'updated', summary, len(changed), changes=changes)


@transaction.atomic
def set_recommended(user, plan_id, recommended):
    """Returns the plan; `plan.activity_id` is the row a Revert would undo, or None."""
    deal = locks.plan_deal(plan_id)
    (target,) = locks.plans(deal, [plan_id])
    rows, data = locks.line(deal, target.line)
    plan = rows[target.id]
    plan.activity_id = None
    if bool(recommended) == plan.recommended:
        return plan
    if recommended and not presented.is_held(plan):  # a current or starred plan already has its column
        adding = presented.added(data, [plan.id])
        refusal = presented.refusal(data, lines.label(plan.line), adding, 'unstar one before recommending another')
        if refusal:
            raise activity.Refused(refusal)
    batch = Batch([plan], ('plan.recommended',))
    plan.recommended = bool(recommended)
    _changed, changes = batch.write()
    verb = 'Recommended' if recommended else 'Removed the recommendation of'
    plan.activity_id = activity.record(deal, user, 'quotes', 'updated', f'{verb} {_words(plan)}', changes=changes).id
    signals.changed(deal.id, [plan.line])
    return plan


def _back_to_proposal(user, deal):
    """Un-selling the last sold plan returns the deal to Proposal: one Activity row, never merged (§5.1)."""
    if deal.stage != 'sold' or deal.plans.filter(sold=True).exists():
        return
    deal.stage = 'proposal'
    deal.save(update_fields=['stage', 'updated_at'])
    change = activity.change(f'deal:{deal.id}', {'stage': ['sold', 'proposal']})
    activity.record(deal, user, 'deal', 'updated', 'Moved to Proposal (no plan is sold now)', changes=[change])


@transaction.atomic
def set_sold(user, plan_id, sold):
    """Mark a plan sold or un-sold. Returns (plan, deal); the deal carries its fresh stage and client."""
    deal = locks.plan_deal(plan_id)
    (plan,) = locks.plans(deal, [plan_id])
    if plan.sold == bool(sold):
        return plan, deal
    refusal = sold and rules.refuses(deal, 'mark_sold')
    if refusal:
        raise activity.Refused(refusal)
    batch = Batch([plan], SALE_KEYS)
    plan.sold, plan.sold_at = bool(sold), clock.now() if sold else None
    _changed, changes = batch.write()
    verb = 'Marked' if sold else 'Un-sold'
    suffix = ' sold' if sold else ''
    activity.record(deal, user, 'quotes', 'sold', f'{verb} {_words(plan)}{suffix}', changes=changes)
    if sold:
        advance(deal, user, 'sold', 'a plan was sold')
    else:
        _back_to_proposal(user, deal)
    sale_changed(user, deal, bool(sold) or client_has_sold(deal.client_id))
    signals.sold(deal.id, [plan.line], getattr(user, 'id', None))
    signals.changed(deal.id, [plan.line])
    return plan, deal
