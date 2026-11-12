"""A person's decision on the client's census answers and the people a client added: census's side of the owner
contract (plan.md §5.3, §5.8; L.6, O.3.1, O.3.4, O.6 #13; L16, L17, L43, L90, C28, C32, C34; OQ85; slice 55).
Review's queues and section bars call these through `review.owners`.

A cell is `(member id, column)`; `(member id, PERSON)` is a whole person a client added (Ch. 12).
- `approve_client(user, deal_id, cells)`: a pending answer moves into `Member.values` with its source `{origin:
  client, by: the approver, link}` through `deals.values.apply()` (rule 2), and the entry becomes `approved`, keeping
  the value it replaced (`prior` and its source) for `revert_approval`. A person a client added becomes a live person
  (their values already carry origin `client` and the link, written when they were added).
- `reject_client(user, deal_id, cells)`: "Keep ours" (L17): the entry is rejected and nothing else changes; a person a
  client added is rejected whole and removed softly, so no read ever lists them.
- `revert_approval(user, deal_id, cells)`: "undo approval" (C28): the value the approval replaced comes back and the
  answer waits again, while the cell still holds the approved value (409 naming the columns otherwise); an approved
  person waits again too.
Activity (area `census`) is key-only, as every census row (rule 4, §3.8): `member:<id>` and the columns, never a value
or a name, so Revert refuses it with its sentence and `revert_approval` is the way back. Lock order: the Deal, then the
people by id, then CensusFacts, rewritten in the transaction (O.3.7).
"""

from collections import namedtuple

from django.db import transaction

from deals import activity, clock
from deals.values import apply as apply_values
from deals.values import source
from intake import client_entries as entries_rule

from .. import facts, fields
from ..client_view import added
from ..models import PERSON, Member
from . import rows

Decided = namedtuple('Decided', 'cells activity')  # cells: [(member id, column)] decided; activity: [Activity rows]

APPROVED, REJECTED, UNAPPROVED = 'approved', 'rejected', 'unapproved'
STILL_CHANGED = '{names} changed after the approval, so it cannot be taken back.'


def _user_id(user):
    return user.id if getattr(user, 'is_authenticated', False) else None


def _locked(deal_id, cells):
    """(Deal, {id: person}) for the live people and the waiting added ones the cells name, locked by id."""
    deal = rows.lock_deal(deal_id)
    ids = sorted({member_id for member_id, _ in cells})
    found = Member.all_objects.select_for_update().filter(deal_id=deal_id, pk__in=ids, removed_at__isnull=True)
    return deal, {member.id: member for member in found.order_by('id')}


def _wanted(people, cells, test):
    out = []
    for member_id, column in dict.fromkeys(cells):
        member = people.get(member_id)
        if member is not None and test(member, column):
            out.append((member, column))
    return out


def _waiting(member, column):
    if column == PERSON:
        return added(member)
    return not added(member) and entries_rule.pending((member.client or {}).get(column))


def _was_approved(member, column):
    return entries_rule.approved((member.client or {}).get(column))


def _record(deal, user, action, summary, decided, count, noun='', coalesce=''):
    by_person = {}
    for member, column in decided:
        by_person.setdefault(member.id, []).append('added' if column == PERSON else column)
    changes = [activity.change(rows.target(member_id), keys) for member_id, keys in by_person.items()]
    return activity.record(
        deal, user, rows.AREA, action, summary, count, coalesce, noun, changes=changes, keys_only=True
    )


def _summary(verb, cells, people):
    parts = []
    if cells:
        parts.append(f'{cells} client census value{"" if cells == 1 else "s"}')
    if people:
        parts.append(f'{people} {"person" if people == 1 else "people"} the client added')
    return f'{verb} {" and ".join(parts)}'


def _save(touched, deal_id):
    for member in touched.values():
        member.save(update_fields=['values', 'sources', 'client', 'removed_at', 'updated_at'])
    facts.refresh(deal_id)


@transaction.atomic
def approve_client(user, deal_id, cells):
    """Returns Decided([(member id, column)], [Activity row])."""
    deal, people = _locked(deal_id, cells)
    decided = _wanted(people, cells, _waiting)
    if not decided:
        return Decided([], [])
    now, by = clock.now().isoformat(), _user_id(user)
    touched = {}
    for member, column in decided:
        client = dict(member.client or {})
        entry = client[column]
        if column != PERSON:
            prior, prior_source = (member.values or {}).get(column, ''), (member.sources or {}).get(column)
            values, sources = dict(member.values), dict(member.sources)
            apply_values(values, sources, {column: entry.get('value', '')}, source('client', user, link=entry['link']))
            member.values, member.sources = values, sources
            client[column] = entries_rule.decided(
                entry, entries_rule.APPROVED, by, now, prior=prior, prior_source=prior_source
            )
        else:
            client[column] = entries_rule.decided(entry, entries_rule.APPROVED, by, now)
        member.client = client
        touched[member.id] = member
    _save(touched, deal_id)
    people_count = sum(1 for _m, column in decided if column == PERSON)
    summary = _summary('Approved', len(decided) - people_count, people_count)
    return Decided([(m.id, c) for m, c in decided], [_record(deal, user, APPROVED, summary, decided, 1)])


@transaction.atomic
def reject_client(user, deal_id, cells):
    """Keep ours, and turn away a person a client added. Returns Decided."""
    deal, people = _locked(deal_id, cells)
    decided = _wanted(people, cells, _waiting)
    if not decided:
        return Decided([], [])
    now, by = clock.now().isoformat(), _user_id(user)
    touched = {}
    for member, column in decided:
        client = dict(member.client or {})
        client[column] = entries_rule.decided(client[column], entries_rule.REJECTED, by, now)
        member.client = client
        if column == PERSON:
            member.removed_at = clock.now()
        touched[member.id] = member
    _save(touched, deal_id)
    people_count = sum(1 for _m, column in decided if column == PERSON)
    cells_count = len(decided) - people_count
    parts = [_summary('Kept our values over', cells_count, 0)] if cells_count else []
    parts += [_summary('turned away', 0, people_count)] if people_count else []
    summary = ' and '.join(parts)
    summary = summary[0].upper() + summary[1:]
    return Decided([(m.id, c) for m, c in decided], [_record(deal, user, REJECTED, summary, decided, 1)])


def _names(columns):
    labels = list(dict.fromkeys(fields.label(column) for column in columns))
    return labels[0] if len(labels) == 1 else ', '.join(labels[:-1]) + ' and ' + labels[-1]


@transaction.atomic
def revert_approval(user, deal_id, cells):
    """Take approvals back. Returns Decided; 409 naming the columns that changed since they were approved."""
    deal, people = _locked(deal_id, cells)
    decided = _wanted(people, cells, _was_approved)
    moved = [
        column
        for member, column in decided
        if column != PERSON
        and not entries_rule.same((member.values or {}).get(column, ''), member.client[column].get('value'))
    ]
    if moved:
        raise activity.Refused(STILL_CHANGED.format(names=_names(moved)), sorted(set(moved)))
    if not decided:
        return Decided([], [])
    touched = {}
    for member, column in decided:
        client = dict(member.client or {})
        entry = client[column]
        if column != PERSON:
            values, sources = dict(member.values), dict(member.sources)
            back = entry.get('prior_source') or source('typed', user)
            apply_values(values, sources, {column: entry.get('prior', '') or ''}, back)
            member.values, member.sources = values, sources
        client[column] = entries_rule.decided(entry, entries_rule.PENDING, None, None)
        member.client = client
        touched[member.id] = member
    _save(touched, deal_id)
    people_count = sum(1 for _m, column in decided if column == PERSON)
    summary = _summary('Took back the approval of', len(decided) - people_count, people_count)
    return Decided([(m.id, c) for m, c in decided], [_record(deal, user, UNAPPROVED, summary, decided, 1)])
