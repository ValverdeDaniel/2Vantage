"""The people part of a link's page (plan.md §8.20; L88–L90; C35; OQ16). Allowlisted: each person asked, by name
(the page that shows people needs the PIN, OQ80), whether a client added them, and only the columns the link asks,
each with its words, its accepted values, whether it is required, the value the page shows and its base. SSN never
appears (OQ16); a date shows as MM/DD/YYYY, as the grid shows it.
"""

from census import client_view as census_view
from census import fields
from census.values import shown as shown_value

from . import words


def _field(member, column, required, link_id, blank):
    value, base, colleague = census_view.cell(member, column, link_id, blank=blank)
    field = fields.BY_KEY[column]
    return {
        'column': column,
        'label': field['label'],
        'type': field['type'],
        'group': field['group'],
        'group_label': words.GROUPS.get(field['group'], ''),
        'help': field.get('help', ''),
        'choices': [{'value': v, 'label': text} for v, text in fields.choices(column)],
        'required': required,
        'value': shown_value(column, value) if value else '',
        'base': base,
        'by_colleague': colleague,
    }


def people(found, link):
    """[{id, title, kind, employee_id, added, fields}] in family order."""
    blank = bool(link.blank)
    out = []
    for member in found.people:
        needed = set(found.needed.get(member.kind, ()))
        out.append(
            {
                'id': member.id,
                'title': census_view.title(member),
                'kind': member.kind,
                'employee_id': member.employee_id,
                'added': census_view.added(member),
                'fields': [
                    _field(member, column, column in needed, link.id, blank) for column in found.columns[member.id]
                ],
            }
        )
    return out


def add_people(found, link_ids):
    """{open, left, relationships} while the page may add people (L90), else None."""
    if not found.add_people:
        return None
    from census.models import Member
    from census.services.client import ADD_LIMIT

    made = Member.all_objects.filter(added_by_link__in=link_ids).count()
    relationships = [{'value': v, 'label': text} for v, text in fields.choices('relationship')]
    return {'left': max(ADD_LIMIT - made, 0), 'relationships': relationships}
