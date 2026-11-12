"""What the census shows a client through a link (plan.md §5.3, §5.8; C35, L88–L90; OQ16). Reads only; the writes are
`services/client.py`.

- `columns(deal, needed)`: {kind: the columns a person of that kind is asked on the portal, in display order}: the
  template's columns (C38: every column but the groups of lines not quoted, plus every required one), less SSN, which is
  never asked or shown on a link (OQ16, plan.md §7.14), and less what a dependent never carries (their employment,
  elections and ZIP follow the employee, §5.3.3).
- `people(deal_id, link_ids, own_link, blank)`: the live people, in family order, then the people a client added
  through one of `link_ids` (the request's links) that still wait for a person; a blank link sees only the people it
  added itself (L66).
- `cell(member, column, link_id, blank)`: (shown value, base, by a colleague): a pending answer over the stored value,
  and on a person a client added, their own values, which wait with them whole (Ch. 12).
"""

from intake import client_entries as entries_rule

from . import fields
from .models import PERSON, Member
from .selectors.page import family_groups
from .template import template_keys


def columns(deal, needed):
    keys = [key for key in template_keys(deal, needed) if key not in fields.SSN_KEYS]
    dependent = [
        key
        for key in keys
        if fields.BY_KEY[key]['group'] not in fields.DEPENDENT_EXEMPT_GROUPS and key not in fields.DEPENDENT_EXEMPT_KEYS
    ]
    return {fields.EMPLOYEE: keys, fields.DEPENDENT: dependent}


def added(member):
    """True while a person a client added waits to be approved or rejected whole."""
    return bool(member.added_by_link) and entries_rule.pending((member.client or {}).get(PERSON))


def _family(people):
    """Each employee followed by their dependents (the carrier files' order), unlinked dependents last."""
    found = [{'id': p.id, 'kind': p.kind, 'employee_id': p.employee_id} for p in people]
    by_id = {person.id: person for person in people}
    return [by_id[person['id']] for family in family_groups(found) for person in family]


def people(deal_id, link_ids, own_link, *, blank=False):
    live = list(Member.objects.filter(deal_id=deal_id).order_by('position', 'id'))
    makers = {own_link} if blank else set(link_ids)
    waiting = [
        member
        for member in Member.all_objects.filter(
            deal_id=deal_id, removed_at__isnull=True, added_by_link__in=makers
        ).order_by('position', 'id')
        if added(member)
    ]
    return _family(live + waiting)


def cell(member, column, link_id, *, blank=False):
    stored = (member.values or {}).get(column, '')
    source = (member.sources or {}).get(column)
    if added(member):
        return stored, entries_rule.base(source, None, link_id), False
    entry = (member.client or {}).get(column)
    return (
        entries_rule.shown(stored, entry, link_id, blank=blank),
        entries_rule.base(source, entry, link_id, blank=blank),
        entries_rule.by_colleague(entry, link_id),
    )


def title(member):
    """How the portal names a person: their name as the census holds it, else their place ("Employee 3")."""
    values = member.values or {}
    name = ' '.join(part for part in (values.get('first_name'), values.get('last_name')) if part)
    return name or ('Dependent' if member.kind == fields.DEPENDENT else 'Employee')
