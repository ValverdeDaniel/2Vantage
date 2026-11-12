"""manage.py scrub_key_only_values [--apply] — hide the values of key-only keys in Activity rows written before those
keys were key-only (plan.md §3.8, rules 4 and 10; slice 47; the PHI gate's checklist, deploy/phi-gate.md).

Until commit c543269 a plan edit recorded `sl_lasers` (claimant data, PHI) with its before and after, like any value.
Since then `deals.activity` keeps every key of `key_only_values` by name only. This command rewrites each older row
through the same function a new row is written with: the edit's other keys keep their before and after, the hidden key
rides beside them as a key-only entry, and the row can no longer be reverted (KEYS_ONLY). Nothing else changes: not
`updated_at`, so "Last updated" and the feed's order stay. Each row is locked while it is rewritten.

A dry run by default; `--apply` writes. It prints counts, areas and row ids, never a value. Run again, it finds nothing.
"""

from collections import Counter

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q, TextField
from django.db.models.functions import Cast

from deals import activity
from deals.models import Activity


def holds_values(changes, keys):
    """True when an entry of `changes` keeps a before and after for one of `keys`."""
    return any(isinstance(entry.get('k'), dict) and keys & set(entry['k']) for entry in changes or [])


def candidates(keys):
    """Ids of the rows whose `changes` keep a value of one of `keys`, oldest first (the text test narrows; Python
    decides)."""
    text = Q()
    for key in keys:
        text |= Q(text__contains=f'"{key}": [')
    rows = Activity.objects.annotate(text=Cast('changes', TextField())).filter(text).order_by('id')
    return [row.id for row in rows.only('id', 'changes').iterator(chunk_size=500) if holds_values(row.changes, keys)]


def scrub(pk, keys):
    """Rewrite one row as deals.activity records a new one, under its lock. Returns (area, action) or None."""
    with transaction.atomic():
        row = Activity.objects.select_for_update().only('id', 'area', 'action', 'changes', 'revertible').get(pk=pk)
        if not holds_values(row.changes, keys):
            return None
        hidden = activity._clean(row.changes, keys_only=False)  # the one writer's own rule (deals/activity.py)
        revertible = row.revertible and not activity.holds_keys_only(hidden)
        Activity.objects.filter(pk=pk).update(changes=hidden, revertible=revertible)
        return row.area, row.action


class Command(BaseCommand):
    help = 'Hide the values of key-only keys (sl_lasers) in older Activity rows. Dry run unless --apply.'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Rewrite the rows (default: only say which).')

    def handle(self, *args, apply=False, **options):
        keys = set(activity.key_only_values)
        if not keys:
            raise CommandError('No key-only keys are registered: run this through manage.py, with every app loaded.')
        found = candidates(keys)
        self.stdout.write(f'Key-only keys: {", ".join(sorted(keys))}.')
        self.stdout.write(f'Activity rows that keep their values: {len(found)}{_ids(found)}')
        if not found:
            return
        if not apply:
            self.stdout.write('Dry run: nothing was written. Run again with --apply to rewrite them.')
            return
        done = Counter(kind for kind in (scrub(pk, keys) for pk in found) if kind)
        for (area, action), count in sorted(done.items()):
            self.stdout.write(f'  {area} / {action}: {count}')
        self.stdout.write(f'Rewrote {sum(done.values())} row(s); {len(candidates(keys))} still keep a value.')


def _ids(found):
    shown = ', '.join(str(pk) for pk in found[:20])
    return f' (ids {shown}{", …" if len(found) > 20 else ""}).' if found else '.'
