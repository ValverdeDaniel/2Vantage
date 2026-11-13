"""Making and closing requests (plan.md §5.8, §7.13; L40, L55–L57, L61, L64, L70; OQ80–OQ82).

`create(user, deal_id, data, dry_run=False)`: one request and a link per person, in one transaction under the Deal's
lock. The body: `people` ([{contact_id} | {name, email?}]; none is a private link to nobody named), `asks` (§6.12's
shape, `rules.asks.clean`), `message` (≤ 1,000), `security` (the person's pick: link or pin), `expires_on`
(YYYY-MM-DD, optional: a picked day holds, so saves no longer slide it) and `blank`. The link takes the stricter of
the pick and `policy.floor(asks)`, so a new link rises to its floor by itself; a nameless link may hold a PIN that
staff keep (Ch. 1). Each link's token and PIN are handed back once, in `Created`; only their hashes stay.
`dry_run` reads the same plan and writes nothing: the builder's live floor (L40).

Refused with 409 when the deal may no longer ask its client (lost, archived or a past year; `deals.rules.
client_asks_open`, B10), else 400 keyed by field. Copying is the send (OQ82): nothing is mailed.

`close(user, request_id, reason)`: answered another way, replaced or cancelled; every link on it stops opening
(L70). Closing a closed request changes nothing.
"""

from collections import namedtuple
from datetime import date

from django.db import transaction
from rest_framework.exceptions import ValidationError

from census.models import Member
from deals import activity, clock, rules
from deals.models import Deal

from .. import tokens, words
from ..models import ClientLink, ClientRequest
from ..rules import ask_words, policy
from ..rules import asks as ask_rules
from . import common, people, pins

Plan = namedtuple('Plan', 'asks people message floor security expires_on blank')
Created = namedtuple('Created', 'request links activity')  # links: [(link, path, pin or '')]
Closed = namedtuple('Closed', 'request changed activity')


def _body(data):
    if not isinstance(data, dict):
        raise ValidationError({'non_field_errors': ['Send the request as an object.']})
    return data


def _day(raw, now, errors):
    if raw in (None, ''):
        return None
    try:
        day = date.fromisoformat(str(raw))
    except ValueError:
        errors['expires_on'] = [words.BAD_DATE]
        return None
    latest = policy.latest_day(now + policy.CEILING, clock.agency_zone())
    if day < clock.today():
        errors['expires_on'] = [words.DATE_PASSED]
    elif day > latest:
        errors['expires_on'] = [words.TOO_LATE.format(day=latest.strftime('%m/%d/%Y'))]
    return day


def _check_cells(deal, asks, errors):
    cells = (asks.get('census') or {}).get('cells') or []
    wanted = {member for member, _column in cells}
    if not wanted:
        return
    found = set(Member.objects.filter(deal=deal, pk__in=wanted).values_list('pk', flat=True))
    if missing := sorted(wanted - found):
        errors['census.cells'] = [words.CELLS_ELSEWHERE.format(ids=', '.join(map(str, missing)))]


def plan(deal, data, now):
    """The request a body asks for, checked, as a Plan. Raises Refused (409) or ValidationError (400)."""
    data = _body(data)
    sentence = rules.client_asks_open(deal)
    if sentence:
        raise activity.Refused(sentence)
    asks, errors = ask_rules.clean(data.get('asks'))
    if not errors:
        _check_cells(deal, asks, errors)
    try:
        who = people.resolve(deal.client_id, data.get('people'))
    except ValidationError as exc:
        errors.update(exc.detail)
        who = []
    message = str(data.get('message') or '').strip()
    if len(message) > policy.MESSAGE_LIMIT:
        errors['message'] = [words.MESSAGE_LONG.format(limit=policy.MESSAGE_LIMIT)]
    pick = data.get('security') or policy.LINK
    if pick not in policy.LEVELS:
        errors['security'] = [words.BAD_LEVEL]
    if data.get('blank') not in (None, True, False):
        errors['blank'] = ['blank must be true or false.']
    expires_on = _day(data.get('expires_on'), now, errors)
    if errors:
        raise ValidationError(errors)
    floor = policy.floor(asks)
    return Plan(asks, who, message, floor, policy.stricter(pick, floor['level']), expires_on, data.get('blank') is True)


def make_link(request, person, planned, user, now):
    """One person's link on `request` at the plan's level, saved; (link, path, pin or '')."""
    expires_at, ceiling_at = policy.first_life(now)
    if planned.expires_on:
        expires_at = policy.picked_expiry(planned.expires_on, ceiling_at, clock.agency_zone())
    seed = tokens.new_seed()
    link = ClientLink(
        request=request,
        token_hash=tokens.digest(tokens.token_of(seed)),
        seed=seed,
        contact=person.contact if person else None,
        name=person.name if person else '',
        email=person.email if person else '',
        security=planned.security,
        blank=planned.blank,
        slides=planned.expires_on is None,
        expires_at=expires_at,
        ceiling_at=ceiling_at,
        created_by_id=common.user_id(user),
        created_at=now,
    )
    pin = pins.issue(link) if planned.security == policy.PIN else ''
    link.save()
    return link, tokens.path_of(seed), pin


def _summary(planned, count):
    asked = ' · '.join(ask_words.words(planned.asks))
    return f'Created a request for {asked}, with {count} link{"" if count == 1 else "s"}'


@transaction.atomic
def create(user, deal_id, data, *, dry_run=False):
    """Created(request, [(link, path, pin)], Activity row), or the Plan alone with `dry_run`."""
    now = clock.now()
    if dry_run:
        return plan(Deal.objects.select_related('client').get(pk=deal_id), data, now)
    deal = Deal.objects.select_for_update(of=('self',)).select_related('client').get(pk=deal_id)
    planned = plan(deal, data, now)
    request = ClientRequest.objects.create(
        deal=deal, asks=planned.asks, message=planned.message, created_by_id=common.user_id(user), created_at=now
    )
    links = [make_link(request, person, planned, user, now) for person in planned.people or [None]]
    change = activity.change(common.request_target(request), ['asks', 'links', 'message'])
    row = activity.record(deal, user, common.AREA, 'created', _summary(planned, len(links)), changes=[change])
    return Created(request, links, row)


@transaction.atomic
def close(user, request_id, reason):
    """Closed(request, {key: [before, after]}, Activity row or None). Raises ValidationError for an unknown reason."""
    if reason not in words.CLOSE_LABELS:
        raise ValidationError({'reason': [words.BAD_REASON.format(reasons=', '.join(words.CLOSE_LABELS))]})
    deal, request = common.locked_request(request_id)
    if request.closed_at is not None:
        return Closed(request, {}, None)
    now = clock.now()
    diff = {
        'closed_at': [None, common.iso(now)],
        'closed_by': [None, common.user_id(user)],
        'close_reason': ['', reason],
    }
    request.closed_at, request.closed_by_id, request.close_reason = now, common.user_id(user), reason
    request.save(update_fields=['closed_at', 'closed_by', 'close_reason'])
    summary = f'Closed a request: {words.CLOSE_LABELS[reason].lower()}'
    row = common.record(deal, user, 'closed', summary, common.request_target(request), diff)
    return Closed(request, diff, row)
