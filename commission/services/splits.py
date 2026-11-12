"""Saving a split (plan.md §5.6, §7.10; H10–H22, H106; OQ70, OQ45): `save_split`, one PUT in one transaction.

- Scope (H20): `deal` stores the deal's own split (an override); `client` stores the client's split, which applies to
  every deal of the client, and drops this deal's override so the client's wins (the old two calls become one).
- Who (OQ70 default): the all tier, or the deal's owner (a client's owner for the client page); 403 otherwise.
- The rows are checked by `rules.validate_rows`, the same check the preview runs (H18, H19). A producer with a login
  and no Party yet gets one now (H11, H95).
- The owner (H22, OQ45): when the primary has a login, a deal split sets `Deal.owner` and a client split sets
  `Client.owner`, through `deals.services.set_owner`, which writes its own Activity row.
Locks the Deal, then the Client, then commission's rows (§3.7's order).
"""

from collections import namedtuple

from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework.exceptions import PermissionDenied, ValidationError

from deals import activity, values
from deals.models import Client, Deal
from deals.services import set_owner

from .. import parties, rules, selectors, vocab
from ..models import ClientSplit, Party
from .rates import AREA, commission_row, target

FORBIDDEN_DEAL = "Only the deal's owner or someone with all commission access can save this split."
FORBIDDEN_CLIENT = "Only the client's owner or someone with all commission access can save the client's split."
BAD_SCOPE = 'Choose this client (all deals) or this deal only.'
Saved = namedtuple('Saved', 'changed activity owner')
STORED = ('role', 'amount', 'renewal_amount', 'basis', 'expires_after_years', 'works_it')


def client_target(client_id):
    return f'client_split:{client_id}'


def _party_id(row, by):
    """The row's Party id; a producer named by their login gets a Party now (H11), with its own Activity row."""
    if row.get('party'):
        return row['party']
    login = get_user_model().objects.get(pk=row['user'])
    party, created = Party.objects.get_or_create(
        user=login,
        defaults={
            'kind': vocab.PRODUCER,
            'name': parties.user_name(login),
            'email': login.email,
            'created_by': by,
        },
    )
    if created:
        activity.record(
            None,
            by,
            AREA,
            'created',
            'Added a producer to Producers & partners',
            changes=[activity.change(f'party:{party.id}', {'active': [None, True]})],
            subject=f'party:{party.id}',
        )
    return party.id


def _stored(rows, by):
    return [{'party': _party_id(row, by), **{key: row[key] for key in STORED}} for row in rows]


def _owner(by, stored, deal, client, scope):
    """Set the owner to the primary's login, when there is one (H22)."""
    login_id = Party.objects.filter(pk=stored[0]['party']).values_list('user_id', flat=True).first()
    if not login_id:
        return {}
    login = get_user_model().objects.get(pk=login_id)
    if scope == vocab.DEAL:
        return set_owner(by, login, deal_id=deal.id)
    return set_owner(by, login, client_id=client.id)


def _summary(scope, deal):
    if scope == vocab.DEAL:
        return 'Saved the producers & splits for this deal'
    return "Saved the client's producers & splits" + (' (applies to every deal)' if deal else '')


@transaction.atomic
def save_split(user, *, deal_id=None, client_id=None, scope=vocab.DEAL, rows=None):
    """Save the rows on the deal (`deal_id`, either scope) or on the client (`client_id`, the client page). Returns
    Saved(changes, Activity | None, the owner's {'owner': [before, after]} or {})."""
    if scope not in vocab.SCOPE_KEYS:
        raise ValidationError({'scope': [BAD_SCOPE]})
    if deal_id is not None:
        deal = values.locked(Deal, deal_id)
        client = values.locked(Client, deal.client_id)
        if not selectors.can_save(user, deal.owner_id):
            raise PermissionDenied(FORBIDDEN_DEAL)
    else:
        deal, scope = None, vocab.CLIENT
        client = values.locked(Client, client_id)
        if not selectors.can_save(user, client.owner_id):
            raise PermissionDenied(FORBIDDEN_CLIENT)
    clean, errors = rules.validate_rows(rows, parties.lookup(parties.people()))
    if errors:
        raise ValidationError({key: [sentence] for key, sentence in errors.items()})
    stored = _stored(clean, user)
    changes = []
    if scope == vocab.DEAL:
        changes += _put_deal(deal, {'rows': stored}, user)
    else:
        changes += _put_client(client, stored, user)
        if deal is not None:
            changes += _put_deal(deal, None, user)  # the client's split applies to this deal again
    entry = None
    if changes:
        # On the deal; from the client page, on the client's latest deal, else a firm row about the client.
        on = deal or client.deals.order_by('-id').first()
        subject = '' if on else f'client:{client.id}'
        entry = activity.record(on, user, AREA, 'updated', _summary(scope, deal), changes=changes, subject=subject)
    return Saved(changes, entry, _owner(user, stored, deal, client, scope))


def _put_deal(deal, split, user):
    row = commission_row(deal)
    if row.split == split:
        return []
    before, row.split, row.updated_by = row.split, split, user
    row.save()
    return [activity.change(target(deal.id), {'split': [before, split]})]


def _put_client(client, stored, user):
    row = ClientSplit.objects.select_for_update().filter(client_id=client.id).first()
    before = row.rows if row else None
    if before == stored:
        return []
    row = row or ClientSplit(client=client)
    row.rows, row.updated_by = stored, user
    row.save()
    return [activity.change(client_target(client.id), {'rows': [before, stored]})]
