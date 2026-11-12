"""What a client adds through their link besides answers: files and people (plan.md §5.8, §7.14; L90, L93, L94;
C35; B12, B22).

- `upload(link_id, slot, file)`: one file for one slot this link asks (`census_file`, or a document slot such as
  `invoice@medical`). It goes through `documents.services.upload`, the only door: the kind's accept list, the first
  bytes, the 30 MB cap and the member-data screen (B12), with source `client`, the link and the slot kept on the row
  so the page names only files that came through its request (B22). Documents records the upload ("Uploaded a Census
  file", by the client). Then the link's save stamp and slide. Nothing reads it yet: client files are read once staff
  ask, or from slice 59.
- `add_people(link_id, people)`: "＋ Add an employee / a dependent" (L90), through census's door; each waits whole
  for a person. One key-only Activity row ("Client added 2 people to the census").
Both lock the link last and refuse (410) when it was turned off or closed meanwhile.
"""

from django.db import transaction
from rest_framework.exceptions import ValidationError

from census.services import client as census_client
from deals import clock
from documents.services import upload as store_upload

from ..models import ClientLink
from ..portal.asked import asked
from ..portal.files_part import CENSUS_SLOT, slot_kind
from . import common, stamps

NOT_ASKED = 'This link does not ask for that file.'
NO_FILE = 'Choose a file to upload.'
NO_PEOPLE = 'This link does not add people to the census.'


def _context(link_id):
    link = ClientLink.objects.select_related('request__deal').get(pk=link_id)
    siblings = list(link.request.links.values_list('id', flat=True))
    return link, link.request, link.request.deal, siblings


@transaction.atomic
def upload(link_id, slot, file):
    """The stored Document. Raises ValidationError (400: a slot not asked, no file, a type the kind refuses, bytes that
    are not what the name says) or FileTooLarge (413); nothing is stored then."""
    link, request, deal, siblings = _context(link_id)
    found = asked(link, request, deal, link_ids=siblings)
    if slot == CENSUS_SLOT:
        if not found.census_file:
            raise ValidationError({'slot': [NOT_ASKED]})
        meta = {'kind': 'census'}
    else:
        if slot not in found.documents:
            raise ValidationError({'slot': [NOT_ASKED]})
        kind, chosen = slot_kind(slot)
        meta = {'kind': kind, 'lines': chosen}
    if file is None:
        raise ValidationError({'file': [NO_FILE]})
    document = store_upload(None, deal, file, meta, source='client', link_id=link.id, slot=slot)
    _deal, _request, link = common.locked_open(link_id)
    stamps.saved(link, clock.now())
    return document


@transaction.atomic
def add_people(link_id, people):
    """[Member] added, each waiting whole."""
    link, request, deal, siblings = _context(link_id)
    found = asked(link, request, deal, link_ids=siblings)
    if not found.add_people:
        raise ValidationError({'people': [NO_PEOPLE]})
    made = census_client.add_people(deal.id, link.id, people, makers=siblings)
    deal, _request, link = common.locked_open(link_id)
    stamps.saved(link, clock.now())
    count = len(made)
    summary = f'Client added {count} {"person" if count == 1 else "people"} to the census'
    keys = [f'member:{member.id}' for member in made]
    stamps.client_row(deal, link, 'client_added', summary, keys, count=count)
    return made
