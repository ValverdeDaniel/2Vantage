"""The roster grid's writes (plan.md §5.3.1, §7.7, §8.21; C4–C7, O.6 #13, #33).

- `edit_values`: a person's cells, typed in ✎ Edit (origin `typed`) or entered for the client while "These came from
  the client" is on (`relay`). Each raw value goes through the one cleaner (`census.values.clean`) and
  `deals.values.apply`: an unchanged value writes nothing, '' clears. `expect` ({key: the value the person saw}) refuses
  the whole write with a 409 naming the columns that changed since, so Undo never writes over someone else (O.6 #33).
  A masked SSN (`***-**-1234`) stands for the number on file when its last four agree, as in an import (C16).
- `add_member`: ＋ Add employee, or ＋ Dep under an employee with the relationship picked (C7).
- `remove_member`: × — a soft removal, the dependents with their employee (O.6 #13); `clear_roster` removes everyone.
Lock order: the Deal, then the people by id, then CensusFacts (O.3.7), rewritten in the same transaction. Activity
(area `census`) records keys only, never a value (§3.7, rule 4), so Revert refuses it; the grid's undo is the way back.
A refusal never names a value, only columns (§3.8).
"""

from collections import namedtuple

from django.db import transaction
from django.db.models import Max
from rest_framework.exceptions import ValidationError

from deals import activity, clock
from deals.values import apply as apply_values
from deals.values import source

from .. import facts, fields
from ..models import Member
from ..values import clean, digits, mask_ssn, masked_last4
from . import rows

Edited = namedtuple('Edited', 'member changed activity')  # changed: the keys whose value changed
Removed = namedtuple('Removed', 'ids activity')

ORIGINS = ('typed', 'relay')
SUMMARY = {'typed': ('Edited', 'census value'), 'relay': ('Entered', "client's census value")}
NOT_VALUES = 'Send the values as an object of census columns.'
NOT_A_COLUMN = 'Some of those are not census columns.'
NOT_TEXT = 'Send the value as text.'
MASKED = 'Type the whole SSN, or leave the masked one as it is.'
STALE = '{names} changed since you last saw {it}, so nothing was saved. Reload to see the new {value}.'
GONE = 'This person is no longer on the census. Reload the roster.'
NO_EMPLOYEE = 'Choose an employee on this census for the dependent.'
NOT_A_KIND = 'A person is an employee or a dependent.'
NOT_CONFIRMED = 'Confirm to remove everyone on the roster.'


def _names(keys):
    labels = [fields.label(key) for key in keys]
    return labels[0] if len(labels) == 1 else ', '.join(labels[:-1]) + ' and ' + labels[-1]


def cleaned(raw):
    """{key: stored text} from the request's raw values; 400 naming each refused column (never its value)."""
    if not isinstance(raw, dict) or not raw:
        raise ValidationError({'values': [NOT_VALUES]})
    if any(key not in fields.BY_KEY for key in raw):
        raise ValidationError({'values': [NOT_A_COLUMN]})  # never echoed: a stray key may be anything
    out, errors = {}, {}
    for key, value in raw.items():
        if isinstance(value, bool) or (value is not None and not isinstance(value, str | int | float)):
            errors[key] = NOT_TEXT
        else:
            out[key] = clean(key, value)
    if errors:
        raise ValidationError({'values': errors})
    return out


def _unmasked(changes, stored):
    """A masked SSN stands for the number on file when its last four agree (C16); else it is refused."""
    errors = {}
    for key in fields.SSN_KEYS:
        last4 = masked_last4(changes.get(key))
        if last4 is None:
            continue
        if digits(stored.get(key))[-4:] == last4:
            changes.pop(key)
        else:
            errors[key] = MASKED
    if errors:
        raise ValidationError({'values': errors})
    return changes


def _same(key, stored, seen):
    """Whether the stored value is what the person saw: as cleaned (dates shown MM/DD/YYYY are stored ISO), or an
    SSN as the screen masked it."""
    stored = stored or ''
    if seen is None or not str(seen).strip():
        return not stored
    if key in fields.SSN_KEYS and str(seen).strip() == mask_ssn(stored):
        return True
    return clean(key, seen) == stored


def _refuse_stale(stored, expect):
    if not isinstance(expect, dict):
        raise ValidationError({'expect': ['Expect must be an object of census columns.']})
    keys = [key for key in fields.KEYS if key in expect and not _same(key, stored.get(key), expect[key])]
    if keys:
        one = len(keys) == 1
        text = STALE.format(names=_names(keys), it='it' if one else 'them', value='value' if one else 'values')
        raise activity.Refused(text, keys)


def _lock_person(member_id):
    """(Deal, the live person), locked in that order; a removed person is refused."""
    deal_id = Member.all_objects.values_list('deal_id', flat=True).get(pk=member_id)
    deal = rows.lock_deal(deal_id)
    member = Member.objects.select_for_update().filter(pk=member_id).first()
    if member is None:
        raise activity.Refused(GONE)
    return deal, member


@transaction.atomic
def edit_values(user, member_id, raw, *, expect=None, origin='typed'):
    """Save the cells that changed on one person. Returns Edited(member, [keys], Activity row or None)."""
    if origin not in ORIGINS:
        raise ValueError(f'Not a hand-edit origin: {origin}')
    changes = cleaned(raw)
    deal, member = _lock_person(member_id)
    if expect is not None:
        _refuse_stale(member.values, expect)
    changes = _unmasked(changes, member.values)
    values, sources = dict(member.values), dict(member.sources)
    changed = apply_values(values, sources, changes, source(origin, user))
    if not changed:
        return Edited(member, [], None)
    member.values, member.sources = values, sources
    member.save(update_fields=['values', 'sources', 'updated_at'])
    facts.refresh(deal.id)
    summary, noun = SUMMARY[origin]
    row = activity.record(
        deal,
        user,
        rows.AREA,
        'edited',
        summary,
        len(changed),
        f'census:values:{origin}',
        noun,
        changes=[activity.change(rows.target(member.id), sorted(changed))],
        keys_only=True,
    )
    return Edited(member, sorted(changed, key=fields.KEYS.index), row)


@transaction.atomic
def add_member(user, deal_id, kind, *, employee_id=None, values=None, origin='typed'):
    """＋ Add employee or ＋ Dep (C7): a new person at the end of the roster (a dependent under its employee).
    Returns (member, Activity row)."""
    if kind not in (fields.EMPLOYEE, fields.DEPENDENT):
        raise ValidationError({'kind': [NOT_A_KIND]})
    changes = cleaned(values) if values else {}
    deal = rows.lock_deal(deal_id)
    employee = None
    if kind == fields.DEPENDENT:
        if isinstance(employee_id, bool) or not isinstance(employee_id, int):
            raise ValidationError({'employee_id': [NO_EMPLOYEE]})
        employee = Member.objects.filter(pk=employee_id, deal_id=deal_id, kind=fields.EMPLOYEE).first()
        if employee is None:
            raise ValidationError({'employee_id': [NO_EMPLOYEE]})
    last = Member.all_objects.filter(deal_id=deal_id).aggregate(at=Max('position'))['at']
    member = Member(deal_id=deal_id, kind=kind, employee=employee, position=0 if last is None else last + 1)
    apply_values(member.values, member.sources, changes, source(origin, user))
    member.save()
    facts.refresh(deal_id)
    what = 'an employee' if kind == fields.EMPLOYEE else 'a dependent'
    row = activity.record(
        deal,
        user,
        rows.AREA,
        'added',
        f'Added {what} to the census',
        changes=[activity.change(rows.target(member.id), ['kind', *member.values])],
        keys_only=True,
    )
    return member, row


def _soft_remove(deal, user, people, summary):
    now = clock.now()
    for person in people:
        person.removed_at, person.updated_at = now, now
    Member.all_objects.bulk_update(people, ['removed_at', 'updated_at'])
    facts.refresh(deal.id)
    return activity.record(
        deal,
        user,
        rows.AREA,
        'removed',
        summary,
        len(people),
        changes=[activity.change(rows.target(person.id), ['removed_at']) for person in people],
        keys_only=True,
    )


@transaction.atomic
def remove_member(user, member_id):
    """× (C7, O.6 #13): the person leaves the roster softly, an employee's dependents with them. Returns Removed."""
    deal, member = _lock_person(member_id)
    ids = [member.id]
    if member.kind == fields.EMPLOYEE:
        ids += list(Member.objects.filter(employee_id=member.id).values_list('id', flat=True))
    people = list(Member.objects.select_for_update().filter(pk__in=ids).order_by('id'))
    others = len(people) - 1
    if member.kind == fields.DEPENDENT:
        summary = 'Removed a dependent from the census'
    elif others:
        summary = f'Removed an employee (and {others} dependent{"" if others == 1 else "s"}) from the census'
    else:
        summary = 'Removed an employee from the census'
    return Removed([person.id for person in people], _soft_remove(deal, user, people, summary))


@transaction.atomic
def clear_roster(user, deal_id, *, confirm=False):
    """Remove everyone on the roster, softly (§7.7). Returns Removed (no Activity when the roster was empty)."""
    if confirm is not True:
        raise ValidationError({'confirm': [NOT_CONFIRMED]})
    deal = rows.lock_deal(deal_id)
    people = list(Member.objects.select_for_update().filter(deal_id=deal_id).order_by('id'))
    if not people:
        return Removed([], None)
    count = len(people)
    summary = f'Cleared the census: {count} {"person" if count == 1 else "people"}'
    return Removed([person.id for person in people], _soft_remove(deal, user, people, summary))
