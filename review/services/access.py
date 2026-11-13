"""Giving someone else access to a request (plan.md §7.13 `POST review/requests/{rid}/people/`; L72; old 891f1b3
`client_request.add_recipients`): they get their own link on the same request, asking the same things — one shared
form, answers in one place (L55).

`add_people(user, deal_id, request_id, people)` → Created(request, [(link, path, pin)], activity): `people` as a new
request takes them (`[{contact_id} | {name, email?}]`, `services.people.resolve`); someone who already holds a link on
this request that can still be used is passed over. Each new link starts its own life (7 days, under its own 30-day
ceiling) at the request's level — what its links already have, never below what it asks (`policy.floor`) — and a PIN
link's PIN is shown this once. At most 20 people on one request. Refused (409) when the deal may no longer ask its
client or the request is closed, 400 when nobody new is named. One key-only Activity row (never a name or address);
not revertible: turn the link off instead.
"""

from django.db import transaction
from rest_framework.exceptions import ValidationError

from deals import activity, clock

from .. import words
from ..models import ClientRequest
from ..rules import policy
from ..rules import tray as tray_rules
from . import common, people, requests

ALREADY = 'They already have a link on this request.'
NOBODY = 'Pick who else should get a link.'


def _holders(links, now):
    """Contact ids and addresses already holding a link here that can still be used."""
    held = [link for link in links if policy.can_renew(link, now)]
    return {link.contact_id for link in held if link.contact_id}, {link.email.lower() for link in held if link.email}


@transaction.atomic
def add_people(user, deal_id, request_id, raw):
    if not ClientRequest.objects.filter(pk=request_id, deal_id=deal_id).exists():
        raise ClientRequest.DoesNotExist
    deal, request = common.locked_request(request_id)
    common.refuse_unless_asking(deal, request)
    links = list(request.links.select_for_update().order_by('id'))
    if not raw:
        raise ValidationError({'people': [NOBODY]})
    now = clock.now()
    contacts, emails = _holders(links, now)
    wanted = [
        person
        for person in people.resolve(deal.client_id, raw)
        if not (person.contact and person.contact.id in contacts)
        and not (person.email and person.email.lower() in emails)
    ]
    if not wanted:
        raise ValidationError({'people': [ALREADY]})
    if len(links) + len(wanted) > policy.MAX_PEOPLE:
        raise ValidationError({'people': [words.TOO_MANY.format(limit=policy.MAX_PEOPLE)]})
    floor = policy.floor(request.asks)
    level = policy.stricter(tray_rules.weakest(links, now), floor['level'])
    planned = requests.Plan(request.asks, wanted, request.message, floor, level, None, False)
    made = [requests.make_link(request, person, planned, user, now) for person in wanted]
    count = len(made)
    summary = f'Gave {count} more {"person" if count == 1 else "people"} access to a request'
    change = activity.change(common.request_target(request), ['links'])
    row = activity.record(
        deal, user, common.AREA, 'people', summary, changes=[change], keys_only=True, revertible=False
    )
    return requests.Created(request, made, row)
