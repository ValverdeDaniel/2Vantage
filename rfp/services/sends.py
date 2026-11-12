"""A draft marked sent, or taken back (plan.md §5.7 "Sent"; K64–K68, K111, K115, K120; G113; OQ52).

`mark_sent(user, deal_id, key, sent)` is the one writer of `RfpRequest.sends`. Marking stores the send's date in agency
time, when and who, the route and who that draft asked (`audience.asked_for`, from the same request the draft was
built from, so editing the picks afterwards never rewrites who was asked: the record Markets checked reads), and the
questionnaires it carried (`questionnaire.selectors.rfp.sent_with`: the signed copy's id, else a hash of the printed
values, G113). The first send pins a route that was following the band and moves the deal to Quoting (`advance`,
forward only; K68); it never marks the deal "Sent to market" (OQ52: the Emails card offers that button). Taking a send
back removes it, for any stored key — a draft that no longer exists included ("Sent earlier", K120); the route and
the stage stay. A lost deal and a past year refuse both (409; K111). One Activity row per call, never merged (K115);
it takes the Emails card's mark off (K10). Lock order: the Deal, then the RfpRequest row.
"""

from collections import namedtuple

from django.db import transaction
from rest_framework.exceptions import NotFound, ValidationError

from deals import activity, clock
from deals import rules as deal_rules
from deals.services.deals import advance
from questionnaire.selectors import rfp as questionnaire_rfp

from .. import audience, drafts
from ..cards import packet
from ..context import Request
from ..models import RfpRequest
from . import AREA, EMAILS, _locked, _take_off, stamp, target

SENT = 'sent'  # the Activity action; no coalesce key, so a send is always its own row
LOST = 'This deal is marked lost — reopen it before recording a send.'
PAST = "This is a past or closed year — record sends on this year's deal."
NO_DRAFT = 'There is no draft for that carrier on this request.'

Sent = namedtuple('Sent', 'sends stage activity')


def _refusal(deal):
    if deal.stage == deal_rules.LOST:
        return LOST
    if deal_rules.is_past(deal):
        return PAST
    return None


def _forms(ctx, rows, draft):
    by_key = {row['key']: row for row in rows}
    carried = [by_key[key] for key in draft['attachment_keys'] if by_key[key]['section'] == 'questionnaires']
    return {row['form']: questionnaire_rfp.sent_with(ctx.deal, row['form']) for row in carried}


def _entry(user, ctx, draft, rows):
    return {
        'on': clock.today().isoformat(),
        'at': clock.now().isoformat(),
        'by': stamp(user)['by'],
        'route': ctx.route,
        'asked': audience.asked_for(ctx, draft['key']),
        'forms': _forms(ctx, rows, draft),
    }


@transaction.atomic
def mark_sent(user, deal_id, key, sent):
    """Returns Sent(every send now, the deal's stage, Activity row or None). Raises ValidationError (400), NotFound
    (404) or activity.Refused (409)."""
    if not isinstance(sent, bool):
        raise ValidationError({'sent': ['sent must be true or false.']})
    deal, row = _locked(deal_id)
    refusal = _refusal(deal)
    if refusal:
        raise activity.Refused(refusal)
    sends = dict((row.sends if row else None) or {})
    if bool(sends.get(key)) == sent:
        return Sent(sends, deal.stage, None)
    if not sent:
        diff = {f'sends.{key}': [sends.pop(key), None]}
        summary = f'Took back the {drafts.label_of(key)} email (not sent)'
    else:
        ctx = Request(deal, row, loaded=True)
        rows = packet.rows(ctx)
        draft = next((found for found in drafts.drafts(ctx, packet.in_packet(rows)) if found['key'] == key), None)
        if draft is None:
            raise NotFound(NO_DRAFT)
        row = row or RfpRequest.objects.create(deal=deal)
        first = not sends
        sends[key] = _entry(user, ctx, draft, rows)
        diff = {f'sends.{key}': [None, sends[key]]}
        if not row.route:
            diff['route'] = ['', ctx.route]
            row.route = ctx.route
        summary = f'Marked the {draft["name"]} email sent'
        if first:
            advance(deal, user, 'quoting', 'the RFP went out')
    row.sends = sends
    diff.update(_take_off(row, {EMAILS}))
    row.save(update_fields=['sends', 'route', 'done', 'updated_at'])
    written = activity.record(deal, user, AREA, SENT, summary, changes=[activity.change(target(deal.id), diff)])
    return Sent(sends, deal.stage, written)
