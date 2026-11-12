"""What review's services share (plan.md §3.7, rule 3): the lock order, the refusals every link action checks, and
the Activity row.

Lock order: the Deal first, then the request, then its links by id (L.6 services). Activity rows (area `review`)
name what happened and the link or request it happened to (`link:<id>`, `request:<id>`), with before and after per
field; never a name, an address, a token or a PIN (§3.8; contacts are key-only in deals' own rows).
"""

from django.db import transaction

from deals import activity, rules
from deals.models import Deal

from .. import words
from ..models import ClientLink, ClientRequest

AREA = 'review'


def iso(moment):
    return moment.isoformat() if moment else None


def user_id(user):
    return user.id if getattr(user, 'is_authenticated', False) else None


def link_target(link):
    return f'link:{link.id}'


def request_target(request):
    return f'request:{request.id}'


def locked_request(request_id):
    """(the Deal, the request), locked in that order. Raises ClientRequest.DoesNotExist."""
    if not transaction.get_connection().in_atomic_block:
        raise RuntimeError('locked_request() must run inside transaction.atomic()')
    deal_id = ClientRequest.objects.values_list('deal_id', flat=True).get(pk=request_id)
    deal = Deal.objects.select_for_update(of=('self',)).select_related('client').get(pk=deal_id)
    return deal, ClientRequest.objects.select_for_update().get(pk=request_id)


def locked_link(link_id):
    """(the Deal, the request, the link), locked in that order. Raises ClientLink.DoesNotExist."""
    request_id = ClientLink.objects.values_list('request_id', flat=True).get(pk=link_id)
    deal, request = locked_request(request_id)
    return deal, request, ClientLink.objects.select_for_update().get(pk=link_id)


def refuse_unless_asking(deal, request):
    """409 when the deal may no longer ask its client (lost, archived, a past year) or the request is closed."""
    sentence = rules.client_asks_open(deal)
    if sentence:
        raise activity.Refused(sentence)
    if request.closed_at is not None:
        raise activity.Refused(words.REQUEST_CLOSED)


def record(deal, user, action, summary, target, diff, *, revertible=True):
    """One Activity row with each field's before and after; review's events never merge."""
    return activity.record(
        deal, user, AREA, action, summary, changes=[activity.change(target, diff)], revertible=revertible
    )
