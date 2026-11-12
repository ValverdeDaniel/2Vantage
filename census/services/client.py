"""A client's census answers and added people through a portal link: census's side of the owner contract (plan.md
§5.3, §5.8; L.6, O.3.1, O.6 #13; C35, L88–L90; OQ16). Review's portal calls these after it has checked what the link
asks.

- `save_client(deal_id, link_id, cells, blank=…, makers=…)`: `cells` is {member id (int): {column: {value,
  base}}}. Every value goes through the one cleaner (`census.values.clean`) and every base is checked before anything
  is written: a value that is not text raises a 400, and a stale base comes back in `conflicts` with nothing saved (the
  same value twice is no conflict). On a live person the answer waits in `Member.client` with the value it would
  replace (`prior`) and never touches `values`; an answer equal to the stored value drops a pending one. A person a
  client added (by one of `makers`, the request's links) waits whole, so their cells are written on the person, origin
  `client`.
- `add_people(deal_id, link_id, people, makers=…)`: "＋ Add an employee / a dependent" (L90): first and last names
  required, at most `ADD_LIMIT` per request; each person waits whole (`client['*']` pending), hidden by the default
  manager until a person approves or rejects them (Ch. 12).
SSN is never taken on a link (OQ16): its columns are refused like a column the link does not ask. Lock order: the Deal,
then the people by id, then CensusFacts (rewritten in the transaction). No Activity here: review records the client's
save and its added people, key-only; the owners record approvals (L.6).
"""

from collections import namedtuple

from django.db import transaction
from django.db.models import Max
from rest_framework.exceptions import ValidationError

from deals import clock
from deals.values import apply as apply_values
from deals.values import source
from intake import client_entries as entries_rule

from .. import facts, fields
from ..client_view import added
from ..models import PERSON, Member
from ..values import clean
from . import rows

Saved = namedtuple('Saved', 'changed conflicts bases')  # changed: [(member id, column)]; conflicts: [{member, column,
# theirs, base}]; bases: {(member id, column): base}

ADD_LIMIT = 50  # people one request may add (old ClientAddPeopleView, L90)
NAME_FIELDS = ('first_name', 'last_name')
NOT_ASKED = 'This link does not ask that.'
NOT_TEXT = 'Send the value as text.'
NOT_SENT = 'Send each answer as {value, base}.'
NAMES = 'Give each person a first and last name.'
NO_EMPLOYEE = 'Choose an employee on this census for the dependent.'
TOO_MANY = f'One request can add up to {ADD_LIMIT} people.'
NOT_PEOPLE = 'Send the people as a list.'


def _cleaned(cells):
    out, errors = {}, {}
    for member_id, columns in cells.items():
        for column, sent in (columns or {}).items():
            ref = f'census:{member_id}:{column}'
            if column not in fields.BY_KEY or column in fields.SSN_KEYS:
                errors[ref] = NOT_ASKED
            elif not isinstance(sent, dict) or 'value' not in sent:
                errors[ref] = NOT_SENT
            elif isinstance(sent['value'], bool) or not isinstance(sent['value'], str | int | float | type(None)):
                errors[ref] = NOT_TEXT
            else:
                out[(member_id, column)] = (clean(column, sent['value']), sent.get('base'))
    if errors:
        raise ValidationError({'answers': errors})
    return out


def _locked_people(deal_id, ids, makers):
    """{id: person} for the live people and the waiting added ones among `ids`, locked by id."""
    found = Member.all_objects.select_for_update().filter(deal_id=deal_id, pk__in=ids, removed_at__isnull=True)
    return {member.id: member for member in found.order_by('id') if not added(member) or member.added_by_link in makers}


def _write_added(member, column, value, link_id):
    changed = apply_values(member.values, member.sources, {column: value}, source('client', link=link_id))
    return bool(changed)


@transaction.atomic
def save_client(deal_id, link_id, cells, *, blank=False, makers=()):
    """Returns Saved. Raises ValidationError (400) before writing; a person not on this deal is NOT_ASKED."""
    cleaned = _cleaned(cells)
    rows.lock_deal(deal_id)
    people = _locked_people(deal_id, sorted({member_id for member_id, _ in cleaned}), set(makers) | {link_id})
    if missing := sorted({f'census:{m}:{c}' for m, c in cleaned if m not in people}):
        raise ValidationError({'answers': dict.fromkeys(missing, NOT_ASKED)})
    now = clock.now().isoformat()
    conflicts, plan = [], []
    for (member_id, column), (value, sent_base) in cleaned.items():
        member = people[member_id]
        stored = member.values.get(column, '')
        src = member.sources.get(column)
        entry = None if added(member) else member.client.get(column)
        shown = stored if added(member) else entries_rule.shown(stored, entry, link_id, blank=blank)
        held = entries_rule.base(src, entry, link_id, blank=blank and not added(member))
        if sent_base != held:
            if not entries_rule.same(shown, value):
                conflicts.append({'member': member_id, 'column': column, 'theirs': shown, 'base': held})
            continue
        plan.append((member, column, value, stored, entry))
    if conflicts:
        return Saved([], conflicts, {})
    changed, touched = [], {}
    for member, column, value, stored, entry in plan:
        if added(member):
            moved = _write_added(member, column, value, link_id)
        else:
            after, moved = entries_rule.next_entry(stored, entry, value, link_id, now, prior=stored)
            if moved:
                client = dict(member.client)
                if after is None:
                    client.pop(column, None)
                else:
                    client[column] = after
                member.client = client
        if moved:
            changed.append((member.id, column))
            touched[member.id] = member
    for member in touched.values():
        member.save(update_fields=['values', 'sources', 'client', 'updated_at'])
    if touched:
        facts.refresh(deal_id)
    bases = {}
    for (member_id, column), _ in cleaned.items():
        member = people[member_id]
        entry = None if added(member) else member.client.get(column)
        bases[(member_id, column)] = entries_rule.base(
            member.sources.get(column), entry, link_id, blank=blank and not added(member)
        )
    return Saved(changed, [], bases)


def _person(raw):
    if not isinstance(raw, dict):
        raise ValidationError({'people': [NOT_PEOPLE]})
    names = {key: clean(key, raw.get(key) if isinstance(raw.get(key), str) else '') for key in NAME_FIELDS}
    if not all(names.values()):
        raise ValidationError({'people': [NAMES]})
    kind = raw.get('kind') if raw.get('kind') in (fields.EMPLOYEE, fields.DEPENDENT) else fields.EMPLOYEE
    values = dict(names)
    if kind == fields.DEPENDENT:
        for key in ('relationship', 'dob'):
            if isinstance(raw.get(key), str) and raw[key].strip():
                values[key] = clean(key, raw[key])
    return kind, raw.get('employee_id'), values


@transaction.atomic
def add_people(deal_id, link_id, people, *, makers=()):
    """New people, each waiting whole. Returns [Member]. Raises ValidationError (400) before writing."""
    if not isinstance(people, list) or not people:
        raise ValidationError({'people': [NOT_PEOPLE]})
    wanted = [_person(raw) for raw in people]
    rows.lock_deal(deal_id)
    makers = set(makers) | {link_id}
    already = Member.all_objects.filter(deal_id=deal_id, added_by_link__in=makers).count()
    if already + len(wanted) > ADD_LIMIT:
        raise ValidationError({'people': [TOO_MANY]})
    employees = {
        member.id
        for member in Member.all_objects.filter(deal_id=deal_id, kind=fields.EMPLOYEE, removed_at__isnull=True)
        if not member.added_by_link or (added(member) and member.added_by_link in makers)
    }
    last = Member.all_objects.filter(deal_id=deal_id).aggregate(at=Max('position'))['at']
    position = 0 if last is None else last + 1
    now = clock.now().isoformat()
    made = []
    for kind, employee_id, values in wanted:
        if kind == fields.DEPENDENT and (isinstance(employee_id, bool) or employee_id not in employees):
            raise ValidationError({'people': [NO_EMPLOYEE]})
        member = Member(
            deal_id=deal_id,
            kind=kind,
            employee_id=employee_id if kind == fields.DEPENDENT else None,
            position=position,
            added_by_link=link_id,
            client={PERSON: {'status': entries_rule.PENDING, 'link': link_id, 'at': now}},
        )
        apply_values(member.values, member.sources, values, source('client', link=link_id))
        member.save()
        made.append(member)
        position += 1
        if kind == fields.EMPLOYEE:
            employees.add(member.id)
    facts.refresh(deal_id)
    return made
