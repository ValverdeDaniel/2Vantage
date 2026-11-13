"""A request as it would be, without writing it (plan.md §7.13; L30, L40, L42; L.6: "Built by the portal's own pure
payload builder, fed a draft ask. Nothing is written then rolled back (P5)").

The builder's and the Ask card's live numbers and their form in the middle read what a link would ask through the
portal's one allowlist (`portal.asked`), on stand-ins that are never saved:
- `stand_ins(deal, asks, request=None, link=None, blank=None, message=None)` → (request, link, link_ids): an open
  request's own rows with the asks swapped in, or for a new link a request and link that do not exist (id -1, so no
  row of theirs is read);
- `carried(deal, asks, ...)` → every ref the page would ask;
- `numbers(deal, asks, ...)` → {intake, blocks, people, values, census_file, documents, total}: what the page asks;
- `page(deal, asks, ...)` → the portal payload (§7.14's KEYS) as staff preview it: `preview` true, nothing writable,
  no follow-ups and no stamp.
Reads only; never a token or a PIN.
"""

from types import SimpleNamespace

from deals import clock
from deals.models import AgencySettings

from ..models import ClientLink
from ..portal import census_part, files_part, intake_part
from ..portal import words as portal_words
from ..portal.asked import asked
from ..rules import policy
from ..rules import portal as portal_rules

NOBODY = -1  # a stand-in's id: no row has it


class _Links:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return list(self.rows)


def stand_ins(deal, asks, *, request=None, link=None, blank=None, message=None):
    now = clock.now()
    if request is None:
        expires, ceiling = policy.first_life(now)
        link = SimpleNamespace(id=NOBODY, blank=bool(blank), expires_at=expires, ceiling_at=ceiling,
                               submitted_at=None, first_submitted_at=None)  # fmt: skip
        stand = SimpleNamespace(id=NOBODY, asks=asks, message=message or '', links=_Links([]), form_version=1)
        return stand, link, []
    siblings = list(ClientLink.objects.filter(request_id=request.id).order_by('id'))
    link = link or (siblings[0] if siblings else None)
    shown = SimpleNamespace(id=link.id, blank=link.blank if blank is None else bool(blank),
                            expires_at=link.expires_at, ceiling_at=link.ceiling_at, submitted_at=link.submitted_at,
                            first_submitted_at=link.first_submitted_at)  # fmt: skip
    message = request.message if message is None else message
    stand = SimpleNamespace(id=request.id, asks=asks, message=message, links=_Links(siblings),
                            form_version=request.form_version)  # fmt: skip
    return stand, shown, [row.id for row in siblings]


def _found(deal, asks, **kwargs):
    request, link, link_ids = stand_ins(deal, asks, **kwargs)
    return asked(link, request, deal, link_ids=link_ids), request, link, link_ids


def carried(deal, asks, **kwargs):
    """Every ref the page would ask (`portal.asked.carried`): what "New · not sent" marks against what it asks now."""
    from ..portal.asked import carried as carried_refs

    return carried_refs(_found(deal, asks, **kwargs)[0])


def numbers(deal, asks, **kwargs):
    found = _found(deal, asks, **kwargs)[0]
    values = sum(len(columns) for columns in found.columns.values())
    out = {
        'intake': len(found.intake_keys),
        'blocks': len(found.blocks),
        'people': len(found.people),
        'values': values,
        'census_file': bool(found.census_file),
        'documents': len(found.documents),
    }
    out['total'] = out['intake'] + out['blocks'] + values + out['documents'] + int(out['census_file'])
    return out


def page(deal, asks, **kwargs):
    found, request, link, link_ids = _found(deal, asks, **kwargs)
    intake = intake_part.section(found, deal, link)
    people = census_part.people(found, link)
    census_file = files_part.census_file(found, link, link_ids)
    documents = files_part.documents(found, link, link_ids)
    row = AgencySettings.get()
    return {
        'agency': {'name': row.name, 'phone': row.phone, 'email': row.email, 'color': row.brand_color},
        'account_name': deal.client.name,
        'expires_at': link.expires_at.isoformat(),
        'days_left': policy.days_left(link.expires_at, clock.now()),
        'submitted_at': None,
        'first_submitted_at': None,
        'can_write': False,
        'staff': True,
        'preview': True,
        'form_stamp': '',
        'message': request.message,
        'colleagues': max(len(link_ids) - 1, 0),
        'answered_elsewhere_at': None,
        'intake': intake,
        'people': people,
        'add_people': census_part.add_people(found, link_ids),
        'census_file': census_file,
        'documents': documents,
        'checklist': portal_rules.rail(portal_words.RAIL, intake, people, census_file, documents, []),
        'follow_ups': [],
    }
