"""Each golden spec's client carries the status the spec names (plan.md §5.1, §13.4; slice 6). Read only."""

from deals import rules
from deals.models import Client, Deal


def test_CL1_the_golden_clients_are_built_with_their_specs_status(db, gd1, gd2):
    for built in (gd1, gd2):
        client = Client.objects.get(pk=built.deal.client_id)
        assert client.relationship == built.spec['status'] == 'prospect'  # GD1 and GD2 are Prospects
        assert (client.client_since, client.converted_by_sale) == (None, False)
        assert rules.deal_type(Deal.objects.get(pk=built.deal.id)) == 'new_business'
