"""One person's link settings (plan.md §7.13 `PATCH links/{id}/`; L39, L61, L63, L66, L69; I35–I39; old 891f1b3
`client_request.set_expiry`, `set_hide_on_file`, `set_nudge`, `correct_address`). Each locks the Deal, the request and
the link in that order (or runs inside a caller that holds them: the Ask card's Update link, `services.form`), writes
one Activity row with each field's before and after, and returns only what changed; asking for what is already so
changes nothing.

- `set_expiry(user, link_id, day)`: the link runs out at 23:59:59 that day in the agency's time, never past its
  30-day ceiling; a picked day stops their saves sliding it (L61). A past day, or one after the ceiling's, is refused.
- `set_blank(user, link_id, blank)`: Blank shows only what they answer, never what else we hold (L66).
- `correct_address(user, link_id, email)`: a mistyped address, only while nobody has opened the link (L63). This link
  only: the contact keeps their own. Key-only Activity (an address never enters Activity, §3.8), not revertible.
- `set_nudge(user, link_id, day)` / `finish_nudge(user, link_id)`: a reminder to nudge the person about their link
  (L69, I35–I39): the day is today or later and before the link runs out, with the link on, its request open and the
  deal still asking its client; `day` None clears it; setting it again moves it to the mover. Finishing stamps it done
  (a ticked reminder stays in the Agenda's Done). These two are the only writers of `ClientLink.nudge` (Agenda's Later
  and ✓ call them).
Refused (409) once the deal may no longer ask its client or the request is closed, and on a link turned off (but a
finished nudge may still be ticked).
"""

from datetime import date

from django.db import transaction
from rest_framework.exceptions import ValidationError

from deals import activity, clock
from deals.services.contacts import EMAIL

from .. import words
from ..rules import policy
from . import common
from .links import Acted

ADDRESS_OPENED = 'Someone has opened this link, so its address stays: give the right person their own link instead.'
NO_NUDGE = 'There is no reminder to nudge on this link.'
NUDGE_LATE = 'Pick a day before the link runs out ({day}): the reminder is for nudging them while it still opens.'
NUDGE_PAST = 'Pick today or a later day.'
NUDGE_ANSWERED = 'They already sent it back: there is nobody to nudge.'
RAN_OUT = 'This link has run out: extend it first, or pick a later date for it.'


def _day(raw, field='day'):
    if raw in (None, ''):
        return None
    try:
        return date.fromisoformat(str(raw))
    except ValueError:
        raise ValidationError({field: [words.BAD_DATE]}) from None


def _live(deal, request, link):
    common.refuse_unless_asking(deal, request)
    if link.revoked_at is not None:
        raise activity.Refused(words.LINK_OFF)


def _row(deal, user, link, action, summary, diff, *, keys_only=False, revertible=True):
    target = common.link_target(link)
    change = activity.change(target, sorted(diff) if keys_only else diff)
    return activity.record(
        deal, user, common.AREA, action, summary, changes=[change], keys_only=keys_only, revertible=revertible
    )


def expiry_of(link, day, now):
    """The expiry a picked day gives this link, or a refusal (ValidationError)."""
    zone = clock.agency_zone()
    latest = policy.latest_day(link.ceiling_at, zone)
    if day < clock.today():
        raise ValidationError({'expires_on': [words.DATE_PASSED]})
    if day > latest:
        raise ValidationError({'expires_on': [words.TOO_LATE.format(day=latest.strftime('%m/%d/%Y'))]})
    return policy.picked_expiry(day, link.ceiling_at, zone)


def put_expiry(deal, user, link, day, now):
    """Inside the caller's locks: {field: [before, after]} written, or {}."""
    moved = expiry_of(link, day, now)
    diff = {}
    if moved != link.expires_at:
        diff['expires_at'] = [common.iso(link.expires_at), common.iso(moved)]
    if link.slides:
        diff['slides'] = [True, False]
    if diff:
        link.expires_at, link.slides = moved, False
        link.save(update_fields=['expires_at', 'slides'])
    return diff


def put_blank(link, blank):
    if bool(link.blank) == bool(blank):
        return {}
    diff = {'blank': [bool(link.blank), bool(blank)]}
    link.blank = bool(blank)
    link.save(update_fields=['blank'])
    return diff


def put_nudge(user, link, day, now):
    """Inside the caller's locks: the nudge set to `day` (None clears it); {'nudge': [before, after]} or {}."""
    before = dict(link.nudge or {})
    if day is None:
        after = {}
    else:
        if link.submitted_at is not None:
            raise activity.Refused(NUDGE_ANSWERED)
        if day < clock.today():
            raise ValidationError({'nudge_on': [NUDGE_PAST]})
        ends = clock.local(link.expires_at).date()
        if day >= ends:
            raise ValidationError({'nudge_on': [NUDGE_LATE.format(day=ends.strftime('%m/%d/%Y'))]})
        if before.get('on') == day.isoformat() and not before.get('done_at'):
            return {}
        after = {'on': day.isoformat(), 'by': common.user_id(user), 'at': common.iso(now)}
    if before == after:
        return {}
    link.nudge = after
    link.save(update_fields=['nudge'])
    return {'nudge': [before, after]}


@transaction.atomic
def set_expiry(user, link_id, day):
    deal, request, link = common.locked_link(link_id)
    day = _day(day, 'expires_on')
    if day is None:
        raise ValidationError({'expires_on': [words.BAD_DATE]})
    _live(deal, request, link)
    now = clock.now()
    if not policy.can_renew(link, now):
        raise activity.Refused(words.PAST_LIMIT)
    diff = put_expiry(deal, user, link, day, now)
    if not diff:
        return Acted(link, request, {}, None)
    summary = f'Set a client link to run out on {day.strftime("%b")} {day.day}'
    return Acted(link, request, diff, _row(deal, user, link, 'expiry', summary, diff))


@transaction.atomic
def set_blank(user, link_id, blank):
    deal, request, link = common.locked_link(link_id)
    if blank not in (True, False):
        raise ValidationError({'blank': ['blank must be true or false.']})
    _live(deal, request, link)
    diff = put_blank(link, blank)
    if not diff:
        return Acted(link, request, {}, None)
    summary = 'Made a client link blank' if blank else 'Made a client link show what we hold'
    return Acted(link, request, diff, _row(deal, user, link, 'blank', summary, diff))


@transaction.atomic
def correct_address(user, link_id, email):
    deal, request, link = common.locked_link(link_id)
    email = str(email or '').strip()
    if not email or len(email) > 254 or not EMAIL.fullmatch(email):
        raise ValidationError({'email': [words.NOT_AN_EMAIL.format(value='That')]})
    _live(deal, request, link)
    if link.opened_at is not None or link.submitted_at is not None:
        raise activity.Refused(ADDRESS_OPENED)
    if link.email == email:
        return Acted(link, request, {}, None)
    diff = {'email': ['', '']}  # key-only: an address never enters Activity
    link.email = email
    link.save(update_fields=['email'])
    row = _row(deal, user, link, 'address', 'Corrected the address on a client link', diff, keys_only=True,
               revertible=False)  # fmt: skip
    return Acted(link, request, {'email': True}, row)


@transaction.atomic
def set_nudge(user, link_id, day):
    """Acted(...). `day`: a date, YYYY-MM-DD, or None to take the reminder off."""
    deal, request, link = common.locked_link(link_id)
    day = day if isinstance(day, date) else _day(day, 'nudge_on')
    if day is not None:
        _live(deal, request, link)
        if not policy.opens(link, clock.now()):
            raise activity.Refused(RAN_OUT)
    diff = put_nudge(user, link, day, clock.now())
    if not diff:
        return Acted(link, request, {}, None)
    summary = (
        f'Set a reminder to nudge a client link on {day.strftime("%b")} {day.day}'
        if day
        else ('Took off a reminder to nudge a client link')
    )
    return Acted(link, request, diff, _row(deal, user, link, 'nudge', summary, diff))


@transaction.atomic
def finish_nudge(user, link_id):
    deal, request, link = common.locked_link(link_id)
    before = dict(link.nudge or {})
    if not before.get('on'):
        raise activity.Refused(NO_NUDGE)
    if before.get('done_at'):
        return Acted(link, request, {}, None)
    after = {**before, 'done_at': common.iso(clock.now()), 'done_by': common.user_id(user)}
    link.nudge = after
    link.save(update_fields=['nudge'])
    diff = {'nudge': [before, after]}
    return Acted(link, request, diff, _row(deal, user, link, 'nudge_done', 'Nudge done', diff))


# `PATCH links/{id}/` actions that take a value (the link actions' table is `links.ACTIONS`): {action: (user, link
# id, body) -> Acted}.
ACTIONS = {
    'expiry': lambda user, link_id, data: set_expiry(user, link_id, data.get('day')),
    'blank': lambda user, link_id, data: set_blank(user, link_id, data.get('blank')),
    'address': lambda user, link_id, data: correct_address(user, link_id, data.get('email')),
    'nudge': lambda user, link_id, data: set_nudge(user, link_id, data.get('day')),
    'nudge_done': lambda user, link_id, data: finish_nudge(user, link_id),  # noqa: ARG005 (the table's signature)
}
