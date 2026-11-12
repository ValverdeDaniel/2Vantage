"""Revert of a documents Activity row (plan.md §3.7; O.3.2; E73, E74): put back a file's kind, role, carrier, lines
or archived state. Registered as `activity.reverters['documents']` in AppConfig.ready().

`deals.activity.revert` has already locked the Deal; this locks each file by id, refuses after a later write to the
same key (naming it), refuses to archive a protected file again, and returns the changes it wrote, which the revert
row records. Uploads, purges and renames (key only) never reach here: the Activity rules refuse them first.
"""

from deals import activity

from .models import Document
from .services.changes import TRACKED, set_archived

LABELS = {'kind': 'Kind', 'role': 'Role', 'carrier': 'Carrier', 'lines': 'Lines', 'archived': 'Removed'}


def revert(row, user):
    later = activity.later_keys(row)
    if later:
        raise activity.changed_since([LABELS.get(key, key) for _target, key in sorted(later)], [k for _t, k in later])
    written = []
    for entry in sorted(row.changes, key=lambda e: e['t']):
        document_id = int(entry['t'].split(':', 1)[1])
        document = Document.all_objects.select_for_update().get(pk=document_id)
        diff = {}
        for key, (before, _after) in entry['k'].items():
            if key == 'archived':
                diff.update(set_archived(document, bool(before), user))
            elif key in TRACKED and getattr(document, key) != before:
                diff[key] = [getattr(document, key), before]
                setattr(document, key, before)
        fields = [key for key in diff if key != 'archived']
        if fields:
            document.save(update_fields=fields)
        if diff:
            written.append(activity.change(entry['t'], diff))
    return written
