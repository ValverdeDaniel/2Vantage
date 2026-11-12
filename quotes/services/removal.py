"""Removing plans, softly (plan.md §5.4; F60, F61, H.6, O.3.7): `plans/delete/` and `plans/clear/`.

- A removed plan keeps its row with `removed_at` set; the default manager hides it from every read.
- Removing a current plan turns its renewal into an alternate and takes it out of every `replaces` list. These are
  real writes in the same Activity row as the removal, so Revert puts them back together (F60). Plans removed in
  the same call are left as they are.
- A sold plan is never removed: it stays and is named, "Unmark sold first" (H.6; the old app's `kept_reason`).
  When every plan named is sold, the call is refused (409) with that sentence.
- Clear line removes every plan on one line except its current and sold plans (F61).
- Restore is Revert of the removal's Activity row (`revert.py`): it refuses, in words, when a rule now blocks it.
- Naming a plan that is already removed changes nothing, so the same call twice writes once.
Each call locks the Deal, then the lines' plans by id, and records one revertible Activity row (action `removed`).
"""

from collections import namedtuple

from django.db import transaction
from rest_framework.exceptions import ValidationError

from deals import activity, clock, lines

from .. import columns, signals
from . import locks
from .batch import Batch
from .roles import no_longer_current

KEYS = (*columns.LINKS, 'plan.removed_at')

# removed: the plans taken off; kept: the sold plans that stay; note: the sentence naming them ('' when none);
# changed: the plans left on the board that changed (a renewal made an alternate, a shorter `replaces` list).
Removal = namedtuple('Removal', 'removed kept note changed row')


def _words(plan):
    return f'{plan.carrier} {plan.name}'


def kept_note(kept):
    if not kept:
        return ''
    names = [_words(plan) for plan in kept]
    joined = names[0] if len(names) == 1 else ', '.join(names[:-1]) + ' and ' + names[-1]
    one = len(names) == 1
    return f'{joined} {"is" if one else "are"} sold, so {"it stays" if one else "they stay"}. Unmark sold first.'


def take_off(rows, removing, now):
    """Mark `removing` removed, in memory, with §5.4's side effects on the plans that stay (`rows`: {id: plan})."""
    gone = {plan.id for plan in removing}
    staying = {pid: plan for pid, plan in rows.items() if pid not in gone}
    for plan in removing:
        if plan.role == 'current':
            no_longer_current(staying, plan)
        plan.removed_at = now


def _summary(removing):
    if len(removing) == 1:
        return f'Removed {_words(removing[0])}'
    line_keys = {plan.line for plan in removing}
    where = f' {lines.label(next(iter(line_keys)))}' if len(line_keys) == 1 else ''
    return f'Removed {len(removing)}{where} plans'


def _remove(user, deal, rows, removing, kept, summary):
    batch = Batch(rows.values(), KEYS)
    take_off(rows, removing, clock.now())
    written, changes = batch.write()
    row = activity.record(deal, user, 'quotes', 'removed', summary, len(removing), changes=changes)
    signals.changed(deal.id, {plan.line for plan in removing})
    gone = {plan.id for plan in removing}
    staying = [plan for plan in written if plan.id not in gone]
    return Removal(removing, kept, kept_note(kept), staying, row)


@transaction.atomic
def delete_plans(user, deal, plan_ids):
    """`plans/delete/` {plan_ids}: removes the named plans, keeping and naming the sold ones. Returns a `Removal`."""
    if not plan_ids:
        raise ValidationError({'plan_ids': ['Name the plans to remove.']})
    deal = locks.deal(deal.id)
    named = locks.named(deal, plan_ids)
    live = [pid for pid, (_line, removed) in named.items() if not removed]
    if not live:
        return Removal([], [], '', [], None)
    rows = locks.lines(deal, {named[pid][0] for pid in live})
    targets = sorted((rows[pid] for pid in live), key=lambda plan: (plan.line, plan.sort_order, plan.id))
    kept = [plan for plan in targets if plan.sold]
    removing = [plan for plan in targets if not plan.sold]
    if not removing:
        raise activity.Refused(kept_note(kept))
    return _remove(user, deal, rows, removing, kept, _summary(removing))


@transaction.atomic
def clear_line(user, deal, line_key):
    """`plans/clear/` {line}: removes every plan on the line except its current and sold plans (F61)."""
    deal = locks.deal(deal.id)
    rows, data = locks.line(deal, line_key)
    quotes = [rows[plan.id] for plan in data.plans if plan.role != 'current']
    kept = [plan for plan in quotes if plan.sold]
    removing = [plan for plan in quotes if not plan.sold]
    if not removing:
        return Removal([], kept, kept_note(kept), [], None)
    summary = f'Cleared {lines.label(line_key)}: removed {len(removing)} plan{"" if len(removing) == 1 else "s"}'
    return _remove(user, deal, rows, removing, kept, summary)
