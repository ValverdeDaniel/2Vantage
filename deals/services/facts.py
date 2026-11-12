"""The deal's header facts and owners (plan.md §6.2, §7.3; M27, M29, H22; OQ45, OQ49): `set_owner` (a deal's or a
client's), `set_facts` (Potential deal size, Agent of record) and their reverter, `reverters['deal_facts']`.

`set_owner` is the one door to `Deal.owner` and `Client.owner`: the header's owner picker and, from slice 48, saving a
commission split whose primary has a login call it (H22). Each write records one Activity row in area `deal_facts`
with before and after, which Revert puts back unless a later write changed the key.
"""

from decimal import Decimal, InvalidOperation

from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework.exceptions import ValidationError

from .. import activity
from ..models import Client, Deal
from ..values import locked
from .snapshots import diff, snapshot

AREA = 'deal_facts'
FACTS = ('deal_size', 'agent_of_record')
AGENT_LIMIT = 200
MAX_SIZE = Decimal('999999999999.99')  # the column's 14 digits, 2 after the point
BAD_SIZE = 'Enter the deal size in dollars, like 250000.'
LABELS = {'deal_size': 'Potential deal size', 'agent_of_record': 'Agent of record', 'owner': 'Owner'}
SUMMARIES = {'deal_size': 'Changed the potential deal size', 'agent_of_record': 'Changed the agent of record'}
REVERTIBLE = {'deal': ('owner', *FACTS), 'client': ('owner',)}
MODELS = {'deal': Deal, 'client': Client}


def clean_deal_size(raw):
    """'$250,000' → Decimal('250000.00'); '' or None clears (None). `$` and commas are stripped (M29)."""
    text = str(raw if raw is not None else '').replace('$', '').replace(',', '').strip()
    if not text:
        return None
    try:
        value = Decimal(text)
    except InvalidOperation as exc:
        raise ValidationError({'deal_size': [BAD_SIZE]}) from exc
    if not value.is_finite() or value < 0 or value > MAX_SIZE:
        raise ValidationError({'deal_size': [BAD_SIZE]})
    return value.quantize(Decimal('0.01'))


def clean_agent(raw):
    """The agent of record as typed, spaces collapsed; '' clears it (the default shows again)."""
    text = ' '.join(str(raw or '').split())
    if len(text) > AGENT_LIMIT:
        raise ValidationError({'agent_of_record': [f'Keep the agent of record under {AGENT_LIMIT} characters.']})
    return text


def _record(user, deal, client, summary, changes):
    """On the deal; a client with no deal gets a firm row about it (`subject`), as the status rows do."""
    subject = '' if deal else f'client:{client.id}'
    return activity.record(deal, user, AREA, 'updated', summary, changes=changes, subject=subject)


@transaction.atomic
def set_owner(user, owner, *, deal_id=None, client_id=None):
    """Set a deal's owner (or, with `client_id`, a client's). Returns {'owner': [before id, after id]}, or {} when
    unchanged. Locks the row. Slice 48's split save calls this when its primary has a login (H22, OQ45)."""
    if (deal_id is None) == (client_id is None):
        raise ValueError('set_owner takes a deal_id or a client_id')
    kind = 'deal' if deal_id is not None else 'client'
    row = locked(MODELS[kind], deal_id if kind == 'deal' else client_id)
    if row.owner_id == getattr(owner, 'id', None):
        return {}
    before = snapshot(row, ('owner_id',))
    row.owner = owner
    row.save(update_fields=['owner', 'updated_at'])
    changed = diff(before, snapshot(row, ('owner_id',)))
    entries = [activity.change(f'{kind}:{row.id}', changed)]
    if kind == 'deal':
        _record(user, row, row.client, 'Changed the owner', entries)
    else:
        _record(user, row.deals.order_by('-id').first(), row, "Changed the client's owner", entries)
    return changed


@transaction.atomic
def set_facts(user, deal_id, **changes):
    """Potential deal size and Agent of record (any subset; typed text or a Decimal, cleaned here). Returns
    {key: [before, after]} for what changed; an unchanged value writes nothing (§3.7)."""
    cleaners = {'deal_size': clean_deal_size, 'agent_of_record': clean_agent}
    deal = locked(Deal, deal_id)
    fields = [key for key in FACTS if key in changes]
    before = snapshot(deal, fields)
    for key in fields:
        setattr(deal, key, cleaners[key](changes[key]))
    changed = diff(before, snapshot(deal, fields))
    if changed:
        deal.save(update_fields=[*changed, 'updated_at'])
        summary = SUMMARIES[next(iter(changed))] if len(changed) == 1 else 'Changed the deal size and agent of record'
        _record(user, deal, deal.client, summary, [activity.change(f'deal:{deal.id}', changed)])
    return changed


def _restore(key, value):
    if key == 'owner':
        if value is None:
            return None
        owner = get_user_model().objects.filter(pk=value).first()
        if owner is None:
            raise activity.Refused('That owner no longer exists, so the change cannot be reverted.')
        return owner
    if key == 'deal_size':
        return None if value is None else Decimal(value)
    return value


def revert(row, user):
    """`reverters['deal_facts']`: put back an owner or a header fact, refused after a later write to the key."""
    later = activity.later_keys(row)
    if later:
        raise activity.changed_since([LABELS.get(key, key) for _t, key in sorted(later)], [key for _t, key in later])
    written = []
    # Lock order: the Deal before the Client (§3.7).
    for entry in sorted(row.changes, key=lambda entry: entry['t'].startswith('client:')):
        kind, _, pk = entry['t'].partition(':')
        keys = entry['k']
        if kind not in REVERTIBLE or any(key not in REVERTIBLE[kind] for key in keys):
            raise activity.Refused(activity.NO_REVERTER)
        target = MODELS[kind].objects.select_for_update().filter(pk=int(pk)).first()
        if target is None:
            raise activity.Refused('This record no longer exists, so the change cannot be reverted.')
        now = snapshot(target, [f'{key}_id' if key == 'owner' else key for key in keys])
        stale = [key for key, (_before, after) in keys.items() if now[key] != after]
        if stale:
            raise activity.changed_since([LABELS.get(key, key) for key in stale], stale)
        for key, (before, _after) in keys.items():
            setattr(target, key, _restore(key, before))
        target.save(update_fields=[*keys, 'updated_at'])
        written.append(activity.change(entry['t'], {key: [after, before] for key, (before, after) in keys.items()}))
    return written
