"""The one merge (plan.md §5.4; F142, O.6 #32): two columns of one line that are one plan become one.

The rate page's row and the SBC's column of one plan (the old app's `plan_remove.merge_plans`, the 2026-10-27 Highmark
renewal). There is no endpoint: the reader's combine and Claude's `merge_plans` call it (slices 18, 19). Pairing is
not merging: a pair's halves stay two plans (D-219).
- Each value the kept plan lacks takes the merged plan's value with its source (file, page, cell, read value; never a
  review mark or an approval). `overwrite` names keys that take the merged value even where the kept plan has one;
  with several merged plans, the first fills a blank and the last wins a named key, as in the old app.
- The kept plan's codes gain the merged plans' codes, so a re-read of either file still finds it; it takes their file
  when it has none.
- The merged plans are then removed, with a removal's side effects (`removal.take_off`), in the same Activity row.
- Refused, in words: a sold plan on either side; a plan of another line; merging into a removed plan. Naming only
  plans already removed changes nothing, so the same call twice writes once.
One revertible Activity row (action `merged`); Revert puts the kept plan back and restores the merged ones.
"""

from django.db import transaction
from rest_framework.exceptions import ValidationError

from deals import activity, clock
from deals.values import apply as apply_values

from .. import fields, signals
from . import locks
from .batch import Batch
from .removal import KEYS as REMOVAL_KEYS
from .removal import take_off

KEYS = (*REMOVAL_KEYS, 'plan.codes', 'plan.source_document')
DROPS = ('mark', 'confirmed')


def _words(plan):
    return f'{plan.carrier} {plan.name}'


def _merged_source(sources):
    def make(key):
        entry = dict(sources[key])
        for name in DROPS:
            entry.pop(name, None)
        return entry

    return make


def _fill(keep, others, forced):
    """({key: value} the kept plan takes, {key: the source entry it comes with})."""
    taken, sources = {}, {}
    for other in others:
        for key, value in other.values.items():
            if value in (None, ''):
                continue
            if (key in keep.values or key in taken) and key not in forced:
                continue
            taken[key] = value
            sources[key] = other.sources.get(key) or {'origin': 'typed'}
    return taken, sources


def _refuse(keep, others, line_key):
    if keep.sold:
        raise activity.Refused(f'{_words(keep)} is sold, so nothing is merged into it. Undo the sale first.')
    for other in others:
        if other.line != line_key:
            raise activity.Refused(f'{_words(other)} is on another line: only plans of one line merge.')
        if other.sold:
            raise activity.Refused(f'{_words(other)} is sold, so it is not merged.')


@transaction.atomic
def merge_plans(user, deal, keep_id, merge_ids, overwrite=()):
    """Folds `merge_ids` into `keep_id`. Returns (the kept plan, [plans left on the board that changed, the kept plan
    first], Activity row or None)."""
    ids = [pid for pid in dict.fromkeys(merge_ids) if pid != keep_id]
    if not ids:
        raise ValidationError({'plan_ids': ['Name the plans to merge into this one.']})
    deal = locks.deal(deal.id)
    named = locks.named(deal, [keep_id, *ids])
    line_key, keep_removed = named[keep_id]
    if keep_removed:
        raise activity.Refused('The plan to merge into has been removed.')
    live = [pid for pid in ids if not named[pid][1]]
    forced = set(overwrite or [])
    unknown = forced - set(fields.keys_for(line_key))
    if unknown:
        raise ValidationError({'overwrite': [f'"{key}" is not a field of this line' for key in sorted(unknown)]})
    rows = locks.lines(deal, {line_key, *(named[pid][0] for pid in live)})
    keep = rows[keep_id]
    if not live:
        return keep, [], None
    others = [rows[pid] for pid in live]
    _refuse(keep, others, line_key)
    batch = Batch(rows.values(), KEYS)
    codes = sorted({*keep.codes, *(code for other in others for code in other.codes)})
    if codes != sorted(keep.codes):
        keep.codes = codes
    if keep.source_document_id is None:
        keep.source_document_id = next((o.source_document_id for o in others if o.source_document_id), None)
    taken, entries = _fill(keep, others, forced)
    values = apply_values(keep.values, keep.sources, taken, _merged_source(entries))
    take_off(rows, others, clock.now())
    changed, changes = batch.write()
    if values:
        keep.save(update_fields=['values', 'sources', 'updated_at'])
        mine = next((entry for entry in changes if entry['t'] == f'plan:{keep.id}'), None)
        if mine is None:
            changes.insert(0, activity.change(f'plan:{keep.id}', values))
        else:
            mine['k'].update(values)
    words = _words(others[0]) if len(others) == 1 else f'{len(others)} plans'
    row = activity.record(deal, user, 'quotes', 'merged', f'Merged {words} into {_words(keep)}', changes=changes)
    signals.changed(deal.id, [line_key])
    gone = {other.id for other in others}
    kept_changed = bool(values) or any(plan.id == keep.id for plan in changed)
    staying = [keep] * kept_changed + [plan for plan in changed if plan.id not in gone | {keep.id}]
    return keep, staying, row
