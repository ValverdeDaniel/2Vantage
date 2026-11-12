"""Producers & partners and the firm defaults (plan.md §6.9, §8.18; H95–H100): `save_party` and `save_settings`.

Both are the all tier's (the views check it). A Party is a firm row: its Activity has no deal and names the party in
`subject` (`party:<id>`), never a person's name in the summary. The house is implicit, so it is never edited here.
The settings save also writes the agency's default rate through `deals.services.set_default_commission` (H100: every
commission default on one screen), and any save confirms the defaults, as the old Settings tab did.
"""

from collections import namedtuple
from decimal import Decimal, InvalidOperation

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.db import transaction
from rest_framework.exceptions import ValidationError

from deals import activity, clock
from deals import comp as comps
from deals.services import set_default_commission

from .. import parties, vocab
from ..models import Party, Settings
from .rates import AREA

TEXT = ('name', 'email', 'phone', 'npn')
FLAGS = ('appointed', 'active')
PCTS = ('first_year_pct', 'renewal_pct')
PARTY_FIELDS = (*TEXT, *FLAGS, 'default_split', *PCTS)
BAD_PCT = 'Enter a percentage from 0 to 100.'
HUNDRED = Decimal(100)
Written = namedtuple('Written', 'row changed activity')


def _pct(raw, allow_blank):
    if raw in (None, '') and allow_blank:
        return None, None
    try:
        value = Decimal(str(raw).replace('%', '').strip())
    except (InvalidOperation, ValueError):
        return None, BAD_PCT
    if not value.is_finite() or value < 0 or value > HUNDRED:
        return None, BAD_PCT
    return value.quantize(Decimal('0.0001')), None


def _text(key, raw, errors):
    text = ' '.join(str(raw or '').split())
    if len(text) > vocab.LIMITS[key]:
        errors[key] = [f'Keep it under {vocab.LIMITS[key]} characters.']
    if key == 'email' and text:
        try:
            validate_email(text)
        except DjangoValidationError:
            errors[key] = ['Enter a valid email address.']
    return text


def clean_party(data):
    """{field: value} for the fields sent; 400 with every error at once."""
    if not isinstance(data, dict):
        raise ValidationError({'non_field_errors': ['Send the fields as an object.']})
    errors, out = {}, {}
    for key in TEXT:
        if key in data:
            out[key] = _text(key, data[key], errors)
    for key in FLAGS:
        if key in data:
            if not isinstance(data[key], bool):
                errors[key] = ['Send true or false.']
            out[key] = data[key] is True
    if 'default_split' in data:
        found, error = comps.parse_comp(data['default_split'], allow_blank=True)
        if error:
            errors['default_split'] = [error]
        out['default_split'] = found
    for key in PCTS:
        if key in data:
            out[key], error = _pct(data[key], allow_blank=True)
            if error:
                errors[key] = [error]
    if 'name' in out and not out['name']:
        errors['name'] = ['Enter a name.']
    if errors:
        raise ValidationError(errors)
    return out


def _json(value):
    return format(value.normalize(), 'f') if isinstance(value, Decimal) else value


def _record(user, party, action, summary, diff):
    return activity.record(
        None,
        user,
        AREA,
        action,
        summary,
        changes=[activity.change(f'party:{party.id}', {k: [_json(b), _json(a)] for k, (b, a) in diff.items()})],
        subject=f'party:{party.id}',
        coalesce_key='' if action == 'created' else f'commission:party:{party.id}',
    )


def _creation(data):
    """The kind and the login of a new party: a partner, or a producer (with a login that has no Party yet)."""
    kind = data.get('kind') or vocab.PRODUCER
    if kind not in vocab.KIND_KEYS:
        raise ValidationError({'kind': ['Choose producer or partner.']})
    login = None
    if data.get('user') not in (None, ''):
        login_id = data['user'] if isinstance(data['user'], int) and not isinstance(data['user'], bool) else None
        login = get_user_model().objects.filter(pk=login_id, is_active=True).first() if login_id else None
        if login is None or kind != vocab.PRODUCER:
            raise ValidationError({'user': ['Pick a producer who can sign in.']})
        if Party.objects.filter(user=login).exists():
            raise ValidationError({'user': ['That producer is already on the list.']})
    return kind, login


@transaction.atomic
def create_party(user, data):
    """＋ Add a partner, or a producer without a login (H96); with `user`, the Party of a producer who has a login
    (an inline edit on a computed roster row, H95). Returns Written(party, {field: [None, value]}, Activity)."""
    kind, login = _creation(data)
    fields = clean_party(data)
    if not fields.get('name'):
        if login is None:
            raise ValidationError({'name': ['Enter a name.']})
        fields['name'] = parties.user_name(login)
    party = Party.objects.create(kind=kind, user=login, created_by=user, **fields)
    if login is not None and not fields.get('email'):
        party.email = login.email
        party.save(update_fields=['email'])
    diff = {key: [None, getattr(party, key)] for key in ('kind', *fields)}
    noun = 'producer' if kind == vocab.PRODUCER else 'partner'
    return Written(party, diff, _record(user, party, 'created', f'Added a {noun} to Producers & partners', diff))


@transaction.atomic
def save_party(user, party_id, data):
    """Edit a party's fields (H97, H98); deactivating is `active: false` (never a delete). Returns Written(party,
    {field: [before, after]}, Activity | None)."""
    fields = clean_party(data)
    party = Party.objects.select_for_update().get(pk=party_id)
    diff = {}
    for key, value in fields.items():
        if getattr(party, key) != value:
            diff[key] = [getattr(party, key), value]
            setattr(party, key, value)
    if not diff:
        return Written(party, {}, None)
    party.save(update_fields=[*diff, 'updated_at'])
    noun = 'producer' if party.kind == vocab.PRODUCER else 'partner'
    return Written(party, diff, _record(user, party, 'updated', f'Edited a {noun} on Producers & partners', diff))


def clean_settings(data):
    if not isinstance(data, dict):
        raise ValidationError({'non_field_errors': ['Send the fields as an object.']})
    errors, out = {}, {}
    for key in set(data) - {*PCTS, 'default_commission', 'confirm'}:
        errors[key] = ['Not a commission setting.']
    for key in PCTS:
        if key in data:
            out[key], error = _pct(data[key], allow_blank=False)
            if error:
                errors[key] = [error]
    if 'default_commission' in data:
        found, error = comps.parse_comp(data['default_commission'], allow_blank=True)
        if error:
            errors['default_commission'] = [error]
        out['default_commission'] = found
    if errors:
        raise ValidationError(errors)
    return out


@transaction.atomic
def save_settings(user, data):
    """The producer % defaults, the agency's default rate and the confirm (H100). Returns Written(settings, changes,
    Activity | None). Saving anything, or `confirm: true`, confirms the defaults."""
    fields = clean_settings(data)
    row = Settings.objects.select_for_update().filter(pk=1).first() or Settings(pk=1)
    diff = {}
    for key in PCTS:
        if key in fields and getattr(row, key) != fields[key]:
            diff[key] = [_json(getattr(row, key)), _json(fields[key])]
            setattr(row, key, fields[key])
    agency = set_default_commission(fields['default_commission']) if 'default_commission' in fields else {}
    if (diff or agency or data.get('confirm') is True) and row.confirmed_at is None:
        diff['confirmed'] = [False, True]
        row.confirmed_by, row.confirmed_at = user, clock.now()
    if diff:
        row.save()
    changes = [activity.change('settings:1', diff)] if diff else []
    changes += [activity.change('agency:1', agency)] if agency else []
    if not changes:
        return Written(row, [], None)
    entry = activity.record(
        None, user, AREA, 'updated', 'Changed the commission defaults', changes=changes, subject='commission:settings'
    )
    return Written(row, changes, entry)
