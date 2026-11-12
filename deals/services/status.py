"""Writing the client status (plan.md §5.1, §6.2, §7.3; CL1–CL9): the status door, the sale's hook and Revert.

`set_status` is the door behind `POST clients/{id}/status/`; `sale_changed` is called by quotes' `set_sold` inside the
sale's transaction, after `advance`; `revert` is `deals.activity.reverters['client']`. All three ask
`deals/lifecycle.py`'s table and write through `_write`, which also lets each deal's `opened_as` follow the status
while no plan is sold. Every write records one `client` Activity row, never merged, holding the before and after of
`relationship`, `client_since` and `converted_by_sale` under `client:<id>` (and each followed deal's `opened_as`).

Lock order (§3.7): the client's Deals by id, then the Client. §5.1 says the door locks only the Client row, but it also
writes `opened_as` on the deals, and taking the Client before a Deal would deadlock with a sale (Deal, then Client).
"""

from datetime import date

from django.db import transaction
from rest_framework.exceptions import ValidationError

from .. import activity, clock, lifecycle, providers, rules
from ..models import Client, Deal
from .snapshots import diff, snapshot

AREA = 'client'
FIELDS = ('relationship', 'client_since', 'converted_by_sale')


def target(client_id):
    return f'client:{client_id}'


def _locked(client_id):
    """(client, deals), locked in the lock order. Raises Client.DoesNotExist."""
    deals = list(Deal.objects.select_for_update().filter(client_id=client_id).order_by('id'))
    return Client.objects.select_for_update().get(pk=client_id), deals


def _write(client, deals, *, status, since, by_sale, follow):
    """Set the three fields and, with `follow`, each deal's `opened_as`; returns the Activity `changes`."""
    before = snapshot(client, FIELDS)
    client.relationship, client.client_since, client.converted_by_sale = status, since, by_sale
    client.save(update_fields=[*FIELDS, 'updated_at'])
    changes = [activity.change(target(client.id), diff(before, snapshot(client, FIELDS)))]
    followed = [deal for deal in deals if follow and deal.opened_as != status]
    if followed:
        Deal.objects.filter(pk__in=[deal.pk for deal in followed]).update(opened_as=status)
        for deal in followed:
            changes.append(activity.change(f'deal:{deal.pk}', {'opened_as': [deal.opened_as, status]}))
            deal.opened_as = status
    return changes


def _record(user, client, deal, action, summary, changes, *, by_sale=False):
    """On the deal (a firm row with `subject` when the client has none). A sale's row refuses Revert (revertible=False
    is how `revert` tells it from a hand row)."""
    return activity.record(
        deal,
        user,
        AREA,
        action,
        summary,
        changes=changes,
        subject='' if deal else target(client.id),
        revertible=not by_sale,
    )


def _since(to, current):
    if to == lifecycle.NEW_CLIENT:
        return clock.today()
    return None if to == lifecycle.PROSPECT else current


@transaction.atomic
def set_status(user, client_id, to):
    """The status door: Convert to client, Back to prospect, or a classification fix (§5.1's table). A move to the
    current status writes nothing. Raises `activity.Refused` (409) with the table's sentence."""
    if to not in lifecycle.LABELS:
        raise ValidationError({'to': [lifecycle.UNKNOWN]})
    client, deals = _locked(client_id)
    current = client.relationship
    if to == current:
        return client
    has_sold = providers.client_has_sold(client.id)
    refusal = lifecycle.refusal(current, to, has_sold=has_sold, lost=rules.convert_refusal(deals))
    if refusal:
        raise activity.Refused(refusal)
    action, summary = lifecycle.hand_move(current, to)
    since = _since(to, client.client_since)
    changes = _write(client, deals, status=to, since=since, by_sale=False, follow=not has_sold)
    _record(user, client, deals[-1] if deals else None, action, summary, changes)
    return client


def sale_changed(user, deal, any_sold):
    """Called by quotes' `set_sold` inside the sale's transaction, after `advance`, with `any_sold`: whether any plan
    on any of the client's deals is still sold. A sale converts a Prospect; un-selling the last sold plan returns a
    client the sale converted to Prospect. Anything else changes nothing. The sold deal's `opened_as` stays frozen.
    Sets `deal.client` to the fresh client (the header the Advisor shows) and returns it."""
    if not transaction.get_connection().in_atomic_block:
        raise RuntimeError("sale_changed runs inside the sale's transaction")
    client, deals = _locked(deal.client_id)
    to = lifecycle.after_sale(client.relationship, client.converted_by_sale, any_sold)
    if to == lifecycle.NEW_CLIENT:
        changes = _write(client, deals, status=to, since=clock.today(), by_sale=True, follow=False)
        _record(user, client, deal, *lifecycle.SALE_CONVERTED, changes, by_sale=True)
    elif to == lifecycle.PROSPECT:
        changes = _write(client, deals, status=to, since=None, by_sale=False, follow=True)
        _record(user, client, deal, *lifecycle.SALE_UNDONE, changes, by_sale=True)
    deal.opened_as = next((row.opened_as for row in deals if row.pk == deal.pk), deal.opened_as)
    deal.client = client
    return client


def revert(row, user):
    """`reverters['client']`: put a hand move's earlier status back, under the door's rules (a Revert of Convert is
    refused while a plan is sold). A status a sale or an un-sale set refuses with its sentence."""
    if not row.revertible:
        raise activity.Refused(lifecycle.UNDO_SALE if row.action == 'converted' else lifecycle.UNDO_UNSALE)
    entry = next((entry for entry in row.changes if entry['t'].startswith('client:')), None)
    if entry is None or 'relationship' not in entry['k']:
        raise activity.Refused(activity.NOTHING_TO_PUT_BACK)
    try:
        client, deals = _locked(int(entry['t'].removeprefix('client:')))
    except (Client.DoesNotExist, ValueError) as exc:
        raise activity.Refused('This client no longer exists, so the change cannot be reverted.') from exc
    before = {key: pair[0] for key, pair in entry['k'].items()}
    after = {key: pair[1] for key, pair in entry['k'].items()}
    if activity.later_keys(row) or client.relationship != after['relationship']:
        raise activity.changed_since(['Status'], ['relationship'])
    has_sold = providers.client_has_sold(client.id)
    to = before['relationship']
    refusal = lifecycle.refusal(client.relationship, to, has_sold=has_sold, lost=rules.convert_refusal(deals))
    if refusal:
        raise activity.Refused(refusal)
    since = before.get('client_since', snapshot(client, FIELDS)['client_since'])
    since = date.fromisoformat(since) if since else None
    by_sale = before.get('converted_by_sale', client.converted_by_sale)
    return _write(client, deals, status=to, since=since, by_sale=by_sale, follow=not has_sold)
