"""The slice-6 migration from New / Existing to the client status (plan.md §6.2): deals' 0003 maps what deals sees,
then quotes' 0002 turns a client with a sold plan into a New client the sale converted. Run here on rows in the old
vocabulary, through the migrations' own functions."""

import importlib
from datetime import UTC, date, datetime

from django.apps import apps
from django.test import override_settings

from conftest import make_deal
from deals.models import Client, Deal
from quotes import services as plans
from quotes.models import Plan

DEALS = importlib.import_module('deals.migrations.0003_client_status')
QUOTES = importlib.import_module('quotes.migrations.0002_client_status_from_sales')


def old_client(user, name, relationship, sold_at=()):
    deal = make_deal(user, name=name)
    Client.objects.filter(pk=deal.client_id).update(relationship=relationship)
    for when in sold_at:
        plan = plans.create_plan(user, deal, line='medical', role='alternate', carrier='Aetna', name=str(when))
        Plan.objects.filter(pk=plan.pk).update(sold=True, sold_at=when)
    return deal


@override_settings(AGENCY_TIME_ZONE='America/New_York')
def test_CL1_the_migration_maps_new_and_existing_to_the_three_statuses(user):
    first, second = datetime(2026, 3, 2, 2, 0, tzinfo=UTC), datetime(2026, 5, 1, 15, 0, tzinfo=UTC)
    new = old_client(user, 'New Co.', 'new')
    served = old_client(user, 'Served Co.', 'existing')
    won = old_client(user, 'Won Co.', 'existing', sold_at=(second, first))
    DEALS.statuses(apps, None)
    QUOTES.clients_with_sales(apps, None)

    def status(deal):
        client = Client.objects.get(pk=deal.client_id)
        opened_as = Deal.objects.get(pk=deal.id).opened_as
        return client.relationship, client.converted_by_sale, client.client_since, opened_as

    assert status(new) == ('prospect', False, None, 'prospect')
    assert status(served) == ('existing_client', False, None, 'existing_client')
    # 21:00 Eastern on 1 March is already 2 March in UTC: the agency's date counts (§3.5).
    assert status(won) == ('new_client', True, date(2026, 3, 1), 'prospect')
    DEALS.back_to_new_and_existing(apps, None)
    assert sorted(Client.objects.values_list('relationship', flat=True)) == ['existing', 'existing', 'new']
