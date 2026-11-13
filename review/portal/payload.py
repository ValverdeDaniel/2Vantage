"""The page a link opens: the one allowlisted payload (plan.md §7.14, §8.20; L76–L110 V2; L108; rule 11).

Its keys are exactly `KEYS` (review's tests pin them; nothing joins without this spec and those tests changing):
- `agency` {name, phone, email}: who sent it and who to ask (P10, L106); never an owner's name;
- `account_name`: the client's name; `expires_at`, `days_left` (L80); `submitted_at`, `first_submitted_at`;
- `can_write`: false on a lost or archived deal or a past year (L105), and for staff; `staff` (L78) and `preview`;
- `form_stamp` (L103); `message`, `colleagues` (a count, never names) and `answered_elsewhere_at` (L82);
- `intake` (intake_part), `people` and `add_people` (census_part), `census_file` and `documents` (files_part), and
  the to-do list `checklist` (rules.portal.rail);
- `follow_ups` (slice 56, follow_ups.py): our notes, send-backs and replies and their questions, by item, as threads.
No team notes, commission, intent, document ids, owner names, other deals' data or files from outside the request.
"""

from deals import clock, rules
from deals.models import AgencySettings

from ..rules import policy
from ..rules import portal as portal_rules
from . import census_part, files_part, follow_ups, intake_part, words
from .asked import asked

KEYS = (
    'agency',
    'account_name',
    'expires_at',
    'days_left',
    'submitted_at',
    'first_submitted_at',
    'can_write',
    'staff',
    'preview',
    'form_stamp',
    'message',
    'colleagues',
    'answered_elsewhere_at',
    'intake',
    'people',
    'add_people',
    'census_file',
    'documents',
    'checklist',
    'follow_ups',
)


def _iso(moment):
    return moment.isoformat() if moment else None


def agency():
    row = AgencySettings.get()
    return {'name': row.name, 'phone': row.phone, 'email': row.email, 'color': row.brand_color}


def build(link, request, deal, *, staff=False, preview=False):
    now = clock.now()
    siblings = list(request.links.all())
    link_ids = [row.id for row in siblings]
    others = [row for row in siblings if row.id != link.id]
    found = asked(link, request, deal, link_ids=link_ids)
    intake = intake_part.section(found, deal, link)
    people = census_part.people(found, link)
    census_file = files_part.census_file(found, link, link_ids)
    documents = files_part.documents(found, link, link_ids)
    answered = [row.submitted_at for row in others if row.submitted_at]
    cards = follow_ups.cards(link, request, deal, found, link_ids=files_part.shown_links(link, link_ids))
    return {
        'agency': agency(),
        'account_name': deal.client.name,
        'expires_at': _iso(link.expires_at),
        'days_left': policy.days_left(link.expires_at, now),
        'submitted_at': _iso(link.submitted_at),
        'first_submitted_at': _iso(link.first_submitted_at),
        'can_write': not (staff or preview) and rules.client_asks_open(deal) is None,
        'staff': bool(staff),
        'preview': bool(preview),
        'form_stamp': portal_rules.form_stamp(link, request, now, follow_ups.stamp(link, request)),
        'message': request.message,
        'colleagues': len(others),
        'answered_elsewhere_at': _iso(min(answered)) if answered else None,
        'intake': intake,
        'people': people,
        'add_people': census_part.add_people(found, link_ids),
        'census_file': census_file,
        'documents': documents,
        'checklist': portal_rules.rail(words.RAIL, intake, people, census_file, documents, cards),
        'follow_ups': cards,
    }
