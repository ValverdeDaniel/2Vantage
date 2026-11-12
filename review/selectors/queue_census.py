"""The census's part of the review queue (plan.md §8.8; L16, C28, C32; old 891f1b3 `CensusClientReview.jsx`,
`items.census_client`): one item per answer waiting on a person's cell, and one per person a client added (approved
or turned away whole, Ch. 12), with their details. An answer in a column a chosen carrier's file requires leads the
queue and names the carriers ("blocks Aetna", `census.providers.carrier_required`); then the census's column order,
then the roster's. Values as the grid shows them (dates MM/DD/YYYY); an SSN only masked. Staff only.
"""

from census import client_view, fields, providers
from census.models import Member
from census.values import mask_ssn
from census.values import shown as census_shown

from ..rules import items as item_rules
from . import queue_common as common

NEW_PEOPLE = 'New people'


def text(column, value):
    if column in fields.SSN_KEYS:
        return mask_ssn(value) if value else ''
    return census_shown(column, value)


def _details(member):
    values = member.values or {}
    return [{'label': fields.label(key), 'value': text(key, values[key])} for key in fields.KEYS if values.get(key)]


def _order(entry, members, carriers):
    member = members.get(entry.member_id)
    blocks = bool(member) and bool((carriers.get(entry.column) or {}).get(member.kind))
    column = fields.KEYS.index(entry.column) if entry.column in fields.KEYS else len(fields.KEYS)
    return (not blocks, entry.person, column, member.position if member else 0, entry.member_id)


def items(deal, entries, links, now):
    members = {member.id: member for member in Member.all_objects.filter(pk__in={e.member_id for e in entries})}
    carriers = providers.carrier_required(deal.id)
    out = []
    for entry in sorted(entries, key=lambda entry: _order(entry, members, carriers)):
        member = members.get(entry.member_id)
        if member is None:
            continue
        title = client_view.title(member)
        kind = 'a dependent' if member.kind == fields.DEPENDENT else 'an employee'
        if entry.person:
            item = common.item(entry, links, now, change=item_rules.ADDED, group='*:added', group_label=NEW_PEOPLE)
            item.update(
                kind='person',
                label=f'New person — {kind}',
                person=title,
                ours='',
                theirs=title,
                details=_details(member),
                blocks=[],
                editable=False,
            )
            out.append(item)
            continue
        held = (member.values or {}).get(entry.column, '')
        change = item_rules.change(held, entry.value)
        label = fields.label(entry.column)
        item = common.item(entry, links, now, change=change, group=f'{entry.column}:{change}', group_label=label)
        item.update(
            kind='answer',
            label=label,
            person=title,
            ours=text(entry.column, held),
            theirs=text(entry.column, entry.value),
            blocks=list((carriers.get(entry.column) or {}).get(member.kind) or []),
            editable=entry.column not in fields.SSN_KEYS,
        )
        out.append(item)
    return out
