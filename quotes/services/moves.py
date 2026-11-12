"""Moving plans to another line of coverage, in place (plan.md §5.4; F59, J159): `plans/move-line/`.

A reader can file a plan under the wrong line (the old app's D-089: life quotes read as medical). The plan keeps its
id, so its Activity, sources and file links stay with it (C10). What names the old line does not travel:
- values outside the new line's fields are dropped (kept in the Activity row);
- its star, its recommendation (the room of the new line holds, as the old app cleared its shortlist flag), its
  links, its typed enrollment, its packages and its option number clear (it is numbered again on the new line,
  J159); a renewal arrives as an alternate;
- the plans it leaves behind lose their link to it: a moved current plan's renewal becomes an alternate and it
  leaves every `replaces` list (§5.4's rule for a plan that stops being current there);
- a current plan joins the end of the new line's current plans; a quote lands last.
Refused, in words naming the plan (the old app's `plan_line.check_move`): a sold plan; a priced version or a copy; an
original that has them; a plan a bundle requires. All or nothing; plans already on the line are skipped, so the same
call twice writes once. One revertible Activity row (action `moved`); Revert puts the plan back with what it lost.
"""

from django.db import transaction
from rest_framework.exceptions import ValidationError

from deals import activity, lines
from deals.values import apply as apply_values

from .. import columns, fields, flags, signals
from ..models import Package, Plan
from . import locks
from .batch import Batch
from .plans import next_number
from .roles import STAR_AND_PICK, no_longer_current

KEYS = ('plan.line', *columns.LINKS, *STAR_AND_PICK, 'plan.sort_order', 'plan.option_number')
ENROLLMENT = 'enrollment.'
CENSUS_NAMES = 'census_names'


def _words(plan):
    return f'{plan.carrier} {plan.name}'


def _refuse(deal, moving):
    """The first refusal among the plans that would move (F59), as the old app words it."""
    for plan in moving:
        if plan.sold:
            raise activity.Refused(
                f'{_words(plan)} is sold: its line was booked with the sale. Undo the sale before moving it.'
            )
        if plan.derived_from_id:
            raise activity.Refused(f"{_words(plan)} is a priced version or a copy: it stays on its original's line.")
    ids = {plan.id for plan in moving}
    derived = list(
        Plan.objects.filter(deal=deal).exclude(derived={}).only('derived_from', 'carrier', 'name', 'derived')
    )
    made_from = {other.derived_from_id for other in derived if other.derived_from_id in ids}
    for plan in moving:
        if plan.id in made_from:
            raise activity.Refused(
                f'{_words(plan)} has priced versions or copies, priced on its {lines.label(plan.line)} rates. '
                'Remove them before moving it.'
            )
    for other in derived:
        required = ids & set(other.derived.get('requires') or [])
        if required:
            plan = next(p for p in moving if p.id in required)
            raise activity.Refused(
                f'{_words(plan)} is required by the bundling discount on {_words(other)}. '
                'Remove that discount before moving it.'
            )


def _strip(plan, to_line):
    """Drop what names the old line from `plan`, in memory; {key: [before, after]} of its values and enrollment."""
    kept = set(fields.keys_for(to_line))
    diff = apply_values(plan.values, plan.sources, {key: '' for key in plan.values if key not in kept}, None)
    for tier, count in plan.enrollment.items():
        diff[f'{ENROLLMENT}{tier}'] = [count, None]
    if plan.census_names:  # the old line's census plan texts (F90)
        diff[CENSUS_NAMES] = [list(plan.census_names), []]
    plan.enrollment, plan.census_names = {}, []
    plan.starred, plan.star_reason, plan.starred_by_id, plan.starred_at = False, '', None, None
    plan.recommended = False
    plan.option_number = None
    plan.role = 'alternate' if plan.role == 'renewal' else plan.role
    plan.renews_id, plan.replaces_ids = None, []
    plan.line = to_line
    return diff


def _leave_packages(moving):
    """{plan id: [package ids it leaves]}; the memberships are deleted (the packages locked by id first)."""
    links = Package.plans.through.objects.filter(plan_id__in=[plan.id for plan in moving])
    memberships = {}
    for plan_id, package_id in links.values_list('plan_id', 'package_id'):
        memberships.setdefault(plan_id, []).append(package_id)
    package_ids = sorted({pid for ids in memberships.values() for pid in ids})
    if package_ids:
        list(Package.objects.select_for_update().filter(id__in=package_ids).order_by('id').values_list('id'))
        links.delete()
    return {plan_id: sorted(ids) for plan_id, ids in memberships.items()}


@transaction.atomic
def move_line(user, deal, plan_ids, to_line):
    """Returns (the moved plans and the plans left behind that changed, Activity row or None)."""
    if to_line not in lines.BY_KEY:
        raise ValidationError({'line': ['Give a line of coverage.']})
    if not plan_ids:
        raise ValidationError({'plan_ids': ['Name the plans to move.']})
    deal = locks.deal(deal.id)
    targets = locks.plans(deal, plan_ids)
    moving_ids = {plan.id for plan in targets if plan.line != to_line}
    if not moving_ids:
        return [], None
    from_lines = {plan.line for plan in targets if plan.id in moving_ids}
    rows = locks.lines(deal, from_lines | {to_line})
    moving = sorted((rows[pid] for pid in moving_ids), key=lambda p: (p.role != 'current', p.line, p.sort_order, p.id))
    _refuse(deal, moving)
    batch = Batch(rows.values(), KEYS)
    staying = {pid: plan for pid, plan in rows.items() if pid not in moving_ids}
    for plan in moving:
        if plan.role == 'current':
            no_longer_current({pid: p for pid, p in staying.items() if p.line == plan.line}, plan)
    extra = {}
    for number, plan in enumerate(moving, start=next_number(deal, to_line)):
        extra[plan.id] = _strip(plan, to_line)
        plan.sort_order = number
    left = _leave_packages(moving)
    for plan in moving:
        if left.get(plan.id):
            extra[plan.id][columns.PACKAGES] = [left[plan.id], []]
    changed, changes = batch.write()
    for plan in moving:
        flags.stamp(plan)  # its open warnings, over the new line's fields (O.3.7)
    Plan.objects.bulk_update(moving, ['values', 'sources', 'enrollment', 'census_names', 'flags'])
    for entry in changes:
        entry['k'].update(extra.get(int(entry['t'].partition(':')[2]), {}))
    label = lines.label(to_line)
    summary = f'Moved {_words(moving[0])} to {label}' if len(moving) == 1 else f'Moved {len(moving)} plans to {label}'
    row = activity.record(deal, user, 'quotes', 'moved', summary, len(moving), changes=changes)
    signals.changed(deal.id, from_lines | {to_line})
    return changed, row
