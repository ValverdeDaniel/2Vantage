"""A client's questionnaire writes through their link besides answers: rows and the officer's signature (plan.md §5.8,
§7.14; G87, G93, L91; slice 58). The portal's views call these once the guard has let the link through; answers ride
`answers.save` with the rest of the page.

- `add_row(link_id, form_key, block)` / `remove_row(link_id, form_key, block, row_id)`: "＋ Add another …" and
  Remove on a form this link asks online, through the questionnaire's own door (`questionnaire.services.client`): a
  row the client adds is theirs to take off while it holds no approved answer (G87).
- `sign(link_id, form_key, name, sign_anyway)`: the company officer's typed signature (G93), through
  `questionnaire.services.sign_from_link`: only on a form asked whole and online (a narrowed ask takes none, a signed
  copy is a file), held by blank required answers until "Sign anyway" (409 with the counts).
Each refuses (400) a form this link does not ask that way, then stamps the link's save (and its slide) and records one
key-only Activity row for the client, never a value or a name (§3.8; the signature's own row names the signer, as
the questionnaire's does).
"""

from django.db import transaction
from django.http import Http404
from rest_framework.exceptions import ValidationError

from deals import clock
from questionnaire.services import client as questionnaire_client
from questionnaire.services import sign_from_link

from ..models import ClientLink
from ..portal.asked import asked
from . import common, stamps

NOT_ASKED = 'This link does not ask for that form.'
NOT_ONLINE = 'This link asks for a signed copy of that form, not answers.'


def _ask(link_id, form_key):
    link = ClientLink.objects.select_related('request__deal').get(pk=link_id)
    request, deal = link.request, link.request.deal
    found = asked(link, request, deal, link_ids=list(request.links.values_list('id', flat=True)))
    ask = next((one for one in found.forms if one.form == form_key), None)
    if ask is None:
        raise Http404(NOT_ASKED)
    if ask.view is None:
        raise ValidationError({'form': [NOT_ONLINE]})
    return link, deal, ask


def _stamp(link_id, action, summary, keys):
    deal, _request, link = common.locked_open(link_id)
    stamps.saved(link, clock.now())
    return stamps.client_row(deal, link, action, summary, keys)


@transaction.atomic
def add_row(link_id, form_key, block):
    link, deal, ask = _ask(link_id, form_key)
    made = questionnaire_client.add_row(deal.id, link.id, form_key, str(block or ''), picks=ask.picks)
    _stamp(link_id, 'client_saved', 'Client added a row to a questionnaire', [f'q:{form_key}:{block}.{made.row_id}'])
    return made.row_id


@transaction.atomic
def remove_row(link_id, form_key, block, row_id):
    link, deal, ask = _ask(link_id, form_key)
    questionnaire_client.remove_row(deal.id, link.id, form_key, block, row_id, picks=ask.picks)
    _stamp(link_id, 'client_saved', 'Client removed a row from a questionnaire', [f'q:{form_key}:{block}.{row_id}'])
    return row_id


@transaction.atomic
def sign(link_id, form_key, name, sign_anyway):
    link, deal, ask = _ask(link_id, form_key)
    if not isinstance(sign_anyway, bool):
        raise ValidationError({'sign_anyway': ['Send true or false.']})
    signed = sign_from_link(
        deal.id, link.id, form_key, name, sign_anyway=sign_anyway, picks=ask.picks, blank=bool(link.blank)
    )
    deal, _request, locked = common.locked_open(link_id)
    stamps.saved(locked, clock.now())
    return signed
