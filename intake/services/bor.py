"""The broker-of-record e-signature (plan.md §5.2, §6.5, §7.6; B29): a typed name stamps who signed, when, and who
recorded it; it can be cleared (B29's fix: the old app stored no user and had no clear). The BOR is on file once it
is signed or a `bor` file is on the deal (§5.2). An earlier year's BOR (B30) waits with renewals.

A lost deal refuses the signature (`deals.rules.refuses(deal, 'sign')`, §5.1); clearing is an internal edit and
passes. Lock order: the Deal, then the Intake row. One Activity row (area `intake`, action `bor`) with the signature's
name, time and recorder before and after under `bor:<deal id>`; intake's reverter puts it back. The signer is the
employer's officer, not a census member (§3.8), so the row keeps the name, as the screen shows it.
"""

from collections import namedtuple

from django.db import transaction
from django.utils.dateparse import parse_datetime
from rest_framework.exceptions import ValidationError

from deals import activity, clock, rules
from deals.services.snapshots import diff

from ..models import Intake
from . import rows

Signed = namedtuple('Signed', 'changed activity')  # changed: {field: [before, after]}, {} when nothing changed

ACTION = 'bor'
NAME_LIMIT = 200
NAME_NEEDED = "Type the signer's full name."
FIELDS = ('name', 'signed_at', 'signed_by')


def target(deal_id):
    return f'bor:{deal_id}'


def state(intake):
    """The signature as Activity keeps it: {name, signed_at (ISO), signed_by (user id)}."""
    return {
        'name': intake.bor_name or '',
        'signed_at': intake.bor_signed_at.isoformat() if intake.bor_signed_at else None,
        'signed_by': intake.bor_signed_by_id,
    }


def _put(intake, values):
    signed_at = values.get('signed_at')
    intake.bor_name = values.get('name') or ''
    intake.bor_signed_at = parse_datetime(signed_at) if isinstance(signed_at, str) else signed_at
    intake.bor_signed_by_id = values.get('signed_by')
    intake.save(update_fields=['bor_name', 'bor_signed_at', 'bor_signed_by', 'updated_at'])


def clean_name(raw):
    name = ' '.join(str(raw if raw is not None else '').split()) if isinstance(raw, (str, int, float)) else ''
    if not name:
        raise ValidationError({'name': [NAME_NEEDED]})
    if len(name) > NAME_LIMIT:
        raise ValidationError({'name': [f'Keep the name under {NAME_LIMIT} characters.']})
    return name


def _record(deal, user, summary, changed):
    return activity.record(deal, user, rows.AREA, ACTION, summary, changes=[activity.change(target(deal.id), changed)])


@transaction.atomic
def sign_bor(user, deal_id, name):
    """Sign the BOR with a typed name. Signing again under the same name changes nothing; another name signs anew.
    Returns Signed(changed, Activity row or None). Raises ValidationError (no name) and Refused (a lost deal)."""
    name = clean_name(name)
    deal = rows.lock_deal(deal_id)
    refusal = rules.refuses(deal, 'sign')
    if refusal:
        raise activity.Refused(refusal)
    intake = rows.lock_intake(deal_id)
    if intake.bor_signed_at is not None and intake.bor_name == name:
        return Signed({}, None)
    before = state(intake)
    by = user.id if getattr(user, 'is_authenticated', False) else None
    _put(intake, {'name': name, 'signed_at': clock.now(), 'signed_by': by})
    changed = diff(before, state(intake))
    return Signed(changed, _record(deal, user, 'Signed the BOR (typed signature)', changed))


@transaction.atomic
def clear_bor(user, deal_id):
    """Clear the signature. Clearing an unsigned BOR changes nothing. Returns Signed(changed, Activity row or None)."""
    deal = rows.lock_deal(deal_id)
    if not Intake.objects.filter(deal_id=deal_id, bor_signed_at__isnull=False).exists():
        return Signed({}, None)
    intake = rows.lock_intake(deal_id)
    before = state(intake)
    _put(intake, {'name': '', 'signed_at': None, 'signed_by': None})
    changed = diff(before, state(intake))
    return Signed(changed, _record(deal, user, 'Cleared the BOR signature', changed))


def revert(deal_id, changed):
    """The signature back to its "before" (intake/revert.py, after the Deal and Intake locks). Returns the diff it
    wrote."""
    intake = rows.lock_intake(deal_id)
    before = state(intake)
    wanted = {**before, **{key: pair[0] for key, pair in changed.items() if key in FIELDS}}
    if wanted == before:
        return {}
    _put(intake, wanted)
    return diff(before, state(intake))
