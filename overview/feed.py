"""The Timeline's rows (plan.md §8.6; M70, M71; slice 63): the deal's Activity, newest first, less the downloads and
views (§3.8; `deals.selectors.activity_feed`, one predicate for the rows and their count), each row with the detail
line the old feed printed under its label — the file's name, the person a link went to and their role, the note's
first line — resolved when the page is read, never stored: Activity's summaries name no people and no files (M.5
B10). A subject that is gone (a removed file, a deleted note) shows none. The details of one page are read together:
one query per kind of subject, whatever the page holds.

`details(rows)` → {activity id: detail} for one page of Activity rows.

`client_feed(client)`: the client page's Timeline (plan.md §8.5; CL21; slice 67): every row of the client's deals,
and the rows about the client itself that sit on no deal (`subject` "client:<id>": a client made with no deal, its
status moves and its split while it has none), newest first, less the downloads and views, as the deal's feed reads.
"""

from django.db.models import Q

from deals import activity
from deals.contacts import label as role_label
from deals.models import Activity, Note
from documents.models import Document
from review.models import ClientLink

FIRST_LINE = 120  # the old feed's cut of a note's first line
TARGETS = ('notes', 'review')  # the areas whose rows name their subject in `changes` (note:<id>, link:<id>)


def _targets(rows):
    """{activity id: [target]} for the rows whose subject rides in `changes` (one query for the page)."""
    wanted = [row.id for row in rows if row.area in TARGETS]
    if not wanted:
        return {}
    found = Activity.objects.filter(pk__in=wanted).values_list('id', 'changes')
    return {pk: [entry.get('t', '') for entry in changes or [] if isinstance(entry, dict)] for pk, changes in found}


def _ids(targets, prefix):
    found = set()
    for names in targets.values():
        for name in names:
            head, _, tail = name.partition(':')
            if head == prefix and tail.isdigit():
                found.add(int(tail))
    return found


def _first_line(body):
    lines = (body or '').strip().splitlines()
    return lines[0][:FIRST_LINE] if lines else ''


def details(rows):
    rows = list(rows)
    targets = _targets(rows)
    files = {row.document_id for row in rows if row.document_id}
    names = {}
    if files:
        for pk, label, original in Document.objects.filter(pk__in=files).values_list('id', 'label', 'original_name'):
            names[pk] = label or original
    notes = {}
    note_ids = _ids(targets, 'note')
    if note_ids:
        notes = {pk: _first_line(body) for pk, body in Note.objects.filter(pk__in=note_ids).values_list('id', 'body')}
    people = {}
    link_ids = _ids(targets, 'link')
    if link_ids:
        for link in ClientLink.objects.filter(pk__in=link_ids).select_related('contact'):
            role = role_label(link.contact.role) if link.contact else ''
            people[link.id] = ' · '.join(part for part in (link.name or link.email, role) if part)
    out = {}
    for row in rows:
        found = names.get(row.document_id, '') if row.document_id else ''
        for name in targets.get(row.id, ()):
            head, _, tail = name.partition(':')
            if not found and tail.isdigit():
                found = (notes if head == 'note' else people if head == 'link' else {}).get(int(tail), '')
        out[row.id] = found
    return out


def client_feed(client):
    """The client's rows, as `deals.selectors.activity_feed` reads a deal's: `changes` left in the database."""
    return (
        Activity.objects.filter(Q(deal__client_id=client.id) | Q(deal__isnull=True, subject=f'client:{client.id}'))
        .exclude(action__in=activity.ACCESS)
        .defer('changes')
        .select_related('actor', 'reverted_by')
        .order_by('-updated_at', '-id')
    )
