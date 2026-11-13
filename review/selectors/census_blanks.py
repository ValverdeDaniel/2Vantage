"""The census blanks edit mode lists, person by person (plan.md §7.13 `GET review/census-blanks/`; L35; old 891f1b3
`request_page.census_blanks`): what a person reads to the client over the phone and types in.

`blanks(deal, required_only=False)` → {people: [{id, title, kind, cells: [{ref, column, label, type, choices,
required}]}], total, shown, truncated}: every live person with a blank cell among the columns the portal asks of their
kind (`census.client_view.columns`: never SSN), the required ones first within a person; at most 500 cells, the rest
counted (`truncated`). Staff only: names a person (edit mode is ours), never a value. Two queries.
"""

from census import client_view as census_view
from census import facts as census_facts
from census import fields as census_fields
from census.models import Member

LIMIT = 500


def blanks(deal, *, required_only=False):
    needed = census_facts.needed(deal)
    columns = census_view.columns(deal, needed)
    people, total, shown = [], 0, 0
    for member in Member.objects.filter(deal_id=deal.id).order_by('position', 'id'):
        wanted = needed.get(member.kind, ())
        empty = [key for key in columns.get(member.kind, ()) if (member.values or {}).get(key) in (None, '')]
        if required_only:
            empty = [key for key in empty if key in wanted]
        empty.sort(key=lambda key: key not in wanted)
        total += len(empty)
        room = max(LIMIT - shown, 0)
        if not empty or not room:
            continue
        cells = [
            {
                'ref': f'census:{member.id}:{key}',
                'column': key,
                'label': census_fields.label(key),
                'type': census_fields.BY_KEY[key]['type'],
                'choices': [{'value': v, 'label': text} for v, text in census_fields.choices(key)],
                'required': key in wanted,
            }
            for key in empty[:room]
        ]
        shown += len(cells)
        people.append({'id': member.id, 'title': census_view.title(member), 'kind': member.kind, 'cells': cells})
    return {'people': people, 'total': total, 'shown': shown, 'truncated': total > shown}
