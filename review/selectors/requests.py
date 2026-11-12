"""Request rows, as the Waiting lane's request card draws them (plan.md §7.13; L7, L8; old `RequestRow`), in a fixed
number of queries however many deals, requests and links are asked: the requests (with who made and closed them) and
the links (with their contacts).

A row: {id, created_at, created_by, message, asks [words], sections, state, first_sent_at, answered_at, answered_by,
closed_at, closed_by, close_reason, expiring, soonest_days, recipients [recipient]}. A recipient: {link_id,
contact_id, name, email, role, security, blank, path, sent, sent_at, opened, opened_at, last_opened_at, opens,
submitted_at, last_saved_at, expires_at, ceiling_at, days_left, expired, revoked, revoked_at, revoked_by, covered,
state, in_progress, can_extend, can_restore}. `path` (`/portal/<token>`, for Copy link) rides only while the link
can still open or be turned back on: never on a closed request's links or past the ceiling. Staff only: no portal
payload reads these rows.
"""

from collections import defaultdict

from deals import contacts

from .. import tokens, words
from ..models import ClientLink, ClientRequest
from ..rules import ask_words, policy
from ..rules import asks as ask_rules
from ..rules import requests as request_rules


def _iso(moment):
    return moment.isoformat() if moment else None


def person(user):
    return (user.get_full_name() or user.username) if user else ''


def load(deal_ids):
    """({deal_id: [request]}, {request_id: [link]}): two queries."""
    found = defaultdict(list)
    for request in ClientRequest.objects.filter(deal_id__in=list(deal_ids)).select_related('created_by', 'closed_by'):
        found[request.deal_id].append(request)
    links = defaultdict(list)
    for link in (
        ClientLink.objects.filter(request__deal_id__in=list(deal_ids))
        .select_related('contact', 'revoked_by')
        .order_by('id')
    ):
        links[link.request_id].append(link)
    return found, links


def recipient(link, now, *, closed, covered):
    renewable = policy.can_renew(link, now)
    return {
        'link_id': link.id,
        'contact_id': link.contact_id,
        'name': link.name,
        'email': link.email,
        'role': contacts.label(link.contact.role) if link.contact else '',
        'security': link.security,
        'blank': link.blank,
        'path': tokens.path_of(link.seed) if not closed and renewable else None,
        'sent': link.sent_at is not None,
        'sent_at': _iso(link.sent_at),
        'opened': link.opened_at is not None,
        'opened_at': _iso(link.opened_at),
        'last_opened_at': _iso(link.last_opened_at),
        'opens': link.open_count,
        'submitted_at': _iso(link.submitted_at),
        'last_saved_at': _iso(link.last_saved_at),
        'expires_at': _iso(link.expires_at),
        'ceiling_at': _iso(link.ceiling_at),
        'days_left': policy.days_left(link.expires_at, now),
        'expired': link.expires_at <= now,
        'revoked': link.revoked_at is not None,
        'revoked_at': _iso(link.revoked_at),
        'revoked_by': person(link.revoked_by),
        'covered': covered,
        'state': request_rules.link_state(link, now, closed=closed, covered=covered),
        'in_progress': request_rules.in_progress(link, now, closed=closed),
        'can_extend': not closed and link.revoked_at is None and renewable,
        'can_restore': not closed and link.revoked_at is not None and renewable,
    }


def row(request, links, now):
    closed = request.closed_at is not None
    answer = min((link for link in links if link.submitted_at), key=lambda link: link.submitted_at, default=None)
    people = [recipient(link, now, closed=closed, covered=bool(answer) and not link.submitted_at) for link in links]
    live = [link for link in links if link.sent_at and not link.submitted_at and policy.opens(link, now, closed=closed)]
    soonest = min((policy.days_left(link.expires_at, now) for link in live), default=None)
    first_sent = min((link.sent_at for link in links if link.sent_at), default=None)
    return {
        'id': request.id,
        'created_at': _iso(request.created_at),
        'created_by': person(request.created_by),
        'message': request.message,
        'asks': ask_words.words(request.asks),
        'sections': ask_rules.sections(request.asks),
        'state': request_rules.request_state(links, request.closed_at, now),
        'first_sent_at': _iso(first_sent),
        'answered_at': _iso(answer.submitted_at) if answer else None,
        'answered_by': answer.name if answer else '',
        'closed_at': _iso(request.closed_at),
        'closed_by': person(request.closed_by),
        'close_reason': request.close_reason,
        'close_reason_label': words.CLOSE_LABELS.get(request.close_reason, ''),
        'expiring': soonest is not None and soonest <= policy.EXPIRING_DAYS,
        'soonest_days': soonest,
        'recipients': people,
    }


def rows(deal_ids, now):
    """{deal_id: [request row]}, oldest request first."""
    found, links = load(deal_ids)
    return {
        deal_id: [row(request, links.get(request.id, []), now) for request in requests]
        for deal_id, requests in found.items()
    }


def one(request_id, now):
    """The row of one request (a write's answer): two queries."""
    request = ClientRequest.objects.select_related('created_by', 'closed_by').get(pk=request_id)
    links = list(
        ClientLink.objects.filter(request_id=request_id).select_related('contact', 'revoked_by').order_by('id')
    )
    return row(request, links, now)
