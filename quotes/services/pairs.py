"""Pair two plans to print as one column, or split them (plan.md §5.4, §7.8 `plans/pair/`; D-219, J15, J161, F137,
O.6 #4; slice 33): "⧉ One column with… · Split" on Pages, and (slice 37) Claude's `pair_plans`.

One plan filed under two plan numbers (Florida Blue's 05182 and 05183) stays two plans: pairing writes only the second
half's `Plan.pair_of`, naming the first, under whose id, place and option number client files print the pair. The old
`plan_merge.set_pair` checks, each refusal by name: both plans live on the deal and on one line, not one plan twice,
one carrier, one kind (two current plans, or two quotes: a current pair's renewals follow it on read), neither in
another pair, at most `MAX_PAIRS` a line. Pairing a pair again writes nothing; Split takes the pair holding a plan
apart, within the line's room (two columns again: refused on a full line, as a star is). Each locks the Deal, then
the line's plans by id, and records one revertible Activity row with `plan.pair_of` before and after.
"""

from django.db import transaction

from deals import activity, lines

from .. import pairs, presented, signals
from ..models import Plan
from . import locks
from .batch import Batch

KEYS = ('plan.pair_of',)
MAX_PAIRS = 8  # the old MAX_GROUPS: a line holds at most eight pairs


def _words(plan):
    return f'{plan.carrier} {plan.name}'.strip()


def _carrier(plan):
    return (plan.carrier or '').strip().lower()  # as typed: "Cigna Dual" is not "Cigna" (the old rule)


def _held(rows):
    """{plan id: its partner's id} for the stored pairs on the line (`rows`: {id: plan}); a pointer at a plan no longer
    live on the line holds nothing."""
    out = {}
    for plan in rows.values():
        first = rows.get(plan.pair_of_id)
        if first is not None and first.id != plan.id:
            out[plan.id], out[first.id] = first.id, plan.id
    return out


def check(first, second):
    """Refused with the sentence when `first` and `second` cannot print as one column (also Claude's `pair_plans`)."""
    if second.line != first.line:
        raise activity.Refused(f'{_words(first)} and {_words(second)} are on different lines.')
    if _carrier(first) != _carrier(second):
        raise activity.Refused(
            f'{_words(first)} and {_words(second)} are from different carriers: only one carrier’s plan filed as two '
            'prints as one.'
        )
    if (first.role == 'current') != (second.role == 'current'):
        raise activity.Refused(
            f'{_words(first)} and {_words(second)} are not the same kind: pair two current plans, or two quotes. A '
            'current pair’s renewals follow it.'
        )


def _record(user, deal, line_key, summary, changed, changes):
    if not changes:
        return None
    signals.changed(deal.id, [line_key])
    return activity.record(deal, user, 'quotes', 'updated', summary, len(changed), changes=changes)


@transaction.atomic
def pair(user, deal, first_id, second_id):
    """Print `second_id` as one column with `first_id` (the column keeps the first's id, place and number).
    Returns (changed plans, Activity row or None); the pair already made writes nothing."""
    deal = locks.deal(deal.id)
    if first_id == second_id:
        locks.plans(deal, [first_id])
        raise activity.Refused('A plan cannot be paired with itself.')
    named = {plan.id: plan for plan in locks.plans(deal, [first_id, second_id])}
    check(named[first_id], named[second_id])
    rows, _data = locks.line(deal, named[first_id].line)
    first, second = rows[first_id], rows[second_id]
    held = _held(rows)
    if held.get(first.id) == second.id:
        return [], None  # already one column: nothing to write
    taken = [plan for plan in (first, second) if plan.id in held]
    if taken:
        names = ' and '.join(_words(plan) for plan in taken)
        verb = 'already prints' if len(taken) == 1 else 'already print'
        raise activity.Refused(f'{names} {verb} as one column with another plan: split it first.')
    if len(held) // 2 >= MAX_PAIRS:
        raise activity.Refused(f'A line holds at most {MAX_PAIRS} pairs.')
    # A plan moved to another line since it was paired still names its half: that pointer goes too.
    stray_ids = Plan.objects.filter(deal=deal, pair_of_id__in=[first.id, second.id]).exclude(line=first.line)
    strays = locks.plans(deal, list(stray_ids.values_list('id', flat=True)))
    batch = Batch([first, second, *strays], KEYS)
    for plan in strays:
        plan.pair_of_id = None
    first.pair_of_id, second.pair_of_id = None, first.id
    changed, changes = batch.write()
    label = lines.label(first.line)
    summary = f'Printed {_words(second)} as one column with {_words(first)} on {label}'
    return changed, _record(user, deal, first.line, summary, changed, changes)


@transaction.atomic
def split(user, deal, plan_id):
    """Take apart the pair holding `plan_id`: both halves print as their own columns again.
    Returns (changed plans, Activity row or None); a plan in no pair is refused by name."""
    deal = locks.deal(deal.id)
    (target,) = locks.plans(deal, [plan_id])
    rows, data = locks.line(deal, target.line)
    plan = rows[target.id]
    partner = _held(rows).get(plan.id)
    if partner is None:
        raise activity.Refused(f'{_words(plan)} is not printed as one column with another plan.')
    second = plan if plan.pair_of_id == partner else rows[partner]
    first = rows[second.pair_of_id]
    held = [p.id for p in presented.held(data)] if presented.has_stars(data) else []
    adding = 1 if (first.id, second.id) in pairs.found(data, held) else 0  # two columns again
    refusal = presented.refusal(data, lines.label(first.line), adding, 'unstar one before splitting this pair')
    if refusal:
        raise activity.Refused(refusal)
    batch = Batch([second], KEYS)
    second.pair_of_id = None
    changed, changes = batch.write()
    summary = f'Split {_words(first)} and {_words(second)} into two columns on {lines.label(first.line)}'
    return changed, _record(user, deal, first.line, summary, changed, changes)
