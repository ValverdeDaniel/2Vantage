"""Applying a census import, after a dry run (plan.md §5.3.2 steps 6–8, §7.7; C16, C17).

`apply_import(user, id, dry_run=True)` builds the file's people under the confirmed mapping, matches them to the
roster and lists who would be added, changed, removed and kept — with, per changed person, the columns that would
change (labels, never values) — and writes nothing. The real apply does the same in one transaction under the locks,
writes the roster, marks the import applied, rewrites `CensusFacts` and records "Imported census: <n> people
(<d> dependents)" with the keys that changed per person, never a value (§3.7, §3.8). The dry run's names are for the
person on the screen only: never Activity, a log or an error.
"""

from collections import namedtuple

from django.db import transaction
from rest_framework.exceptions import ValidationError

from ai.models import Job
from deals import activity, clock

from .. import facts, fields, matching
from ..importer import people as people_of
from ..models import CensusImport, Member
from ..reader import staged
from . import roster, rows

NOBODY = 'No one was found under this mapping. Map the name columns, or check the first data row.'

Applied = namedtuple('Applied', 'stats activity')


def _plural(count, one, many):
    return f'{count} {one if count == 1 else many}'


def build(imp, members):
    """(people, masked-SSN summary) for the import under its mapping, against the roster `members`. A roster Claude
    read is built from its people as read (census.reader.staged, slice 51), a file from its rows."""
    live = [entry for entry in rows.roster_entries(members) if not entry['removed']]
    on_file = people_of.SsnOnFile(live)
    if rows.is_read(imp):
        built = staged.people(imp.read, imp.mapping, on_file)
    else:
        found = rows.opened(imp)
        built = people_of.build(found.table, imp.mapping, on_file, cells=not found.recipe.get('applied'))
    if not built:
        raise ValidationError({'mapping': [NOBODY]})
    return built, on_file.summary()


def _person(values, kind, member_id=None, **extra):
    out = {'name': people_of.label(values), 'kind': kind, **extra}
    if member_id is not None:
        out['id'] = member_id
    return out


def report(built, found, entries, masked):
    """The dry run's answer (§7.7): {added, changed, removed, kept, cells_changed, counts, masked_ssns}."""
    by_id = {entry['id']: entry for entry in entries}
    added = [_person(built[i]['values'], built[i]['kind'], restored=False) for i in found.created] + [
        _person(by_id[m]['values'], by_id[m]['kind'], m, restored=True) for m in sorted(found.restored)
    ]
    changed, cells = [], {}
    for index, member_id in found.matched.items():
        if member_id in found.restored or not found.changes[index]:
            continue
        columns = [fields.label(key) for key in fields.KEYS if key in found.changes[index]]
        changed.append(_person(by_id[member_id]['values'], built[index]['kind'], member_id, columns=columns))
        cells[str(member_id)] = columns
    removed = [_person(by_id[m]['values'], by_id[m]['kind'], m) for m in found.removed]
    kept = [_person(by_id[m]['values'], by_id[m]['kind'], m, why=found.why[m]) for m in found.kept]
    counts = {
        'people': len(built),
        'employees': sum(1 for person in built if person['kind'] == fields.EMPLOYEE),
        'dependents': sum(1 for person in built if person['kind'] == fields.DEPENDENT),
        'added': len(added),
        'changed': len(changed),
        'unchanged': len(found.matched) - len(changed) - len(found.restored),
        'removed': len(removed),
        'kept': len(kept),
    }
    return {
        'added': added,
        'changed': changed,
        'removed': removed,
        'kept': kept,
        'cells_changed': cells,
        'counts': counts,
        'masked_ssns': masked,
    }


def dry_run(import_id):
    """What applying would do; writes nothing."""
    imp = CensusImport.objects.get(pk=import_id)
    rows.proposed(imp)
    members = list(Member.all_objects.filter(deal_id=imp.deal_id).order_by('id'))
    built, masked = build(imp, members)
    entries = rows.roster_entries(members)
    return report(built, matching.match(built, entries), entries, masked)


@transaction.atomic
def apply_import(user, import_id, *, resolve_job=True):
    """Apply a proposed import (§5.3.2 step 8). Returns Applied(stats, activity). An import a Claude read staged marks
    its read used too, as "Use this scan ▸" would (`resolve_job` False when that is the caller; slice 51)."""
    imp = CensusImport.objects.get(pk=import_id)
    deal = rows.lock_deal(imp.deal_id)
    if imp.job_id:
        Job.objects.select_for_update().filter(pk=imp.job_id).first()  # the read, before the import (the lock order)
    imp = rows.lock_import(import_id)
    rows.proposed(imp)
    members = rows.lock_members(deal.id)
    built, masked = build(imp, members)
    found = matching.match(built, rows.roster_entries(members))
    written = roster.write(user, deal.id, imp.document_id, built, found, members)
    imp.status, imp.applied_at = CensusImport.APPLIED, clock.now()
    imp.stats = {**written.stats, 'masked_ssns': masked}
    imp.read = rows.emptied(imp.read)  # its people are on the roster now (D74, B13)
    imp.save(update_fields=['status', 'applied_at', 'stats', 'read'])
    facts.refresh(deal.id)
    people, dependents = written.stats['rows'], written.stats['dependents']
    counted = f'{_plural(people, "person", "people")} ({_plural(dependents, "dependent", "dependents")})'
    row = activity.record(
        deal,
        user,
        rows.AREA,
        'imported',
        f'Imported census: {counted}',
        changes=written.changes,
        keys_only=True,
        document_id=imp.document_id,
    )
    if imp.job_id and resolve_job:
        from ai.services.landing import owner_applied

        owner_applied(user, imp.job_id, landed(imp, row, counted))
    return Applied(imp.stats, row)


def landed(imp, row, counted):
    """What a census read's job keeps once its import is applied: counts, never a person (D74). A census import is
    not undone by the read's ↶ Undo this run: a person imports the file they want again (`undo` False)."""
    return {
        'activity_id': row.id,
        'activity_ids': [row.id],
        'areas': ['census', 'activity'],
        'summary': f'census: {counted}',
        'skipped': [],
        'plan_ids': [],
        'import_id': imp.id,
        'undo': False,
    }
