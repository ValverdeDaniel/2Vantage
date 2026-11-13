"""Quotes' facts for Agenda and the Overview (plan.md §5.10; I50, I53, I55, I63): quotes in, the quote files still
unread, the values to look at, the sold lines and the plans no enrollment prices, on GD3's checkpoints (Q.3 #5) and
factory deals."""

import pytest

from conftest import make_deal
from documents.models import Document
from quotes import services, summary

pytestmark = pytest.mark.django_db


def test_I50_I53_GD3_at_A_has_quotes_in_an_unread_packet_and_every_plan_priced(quote_first):
    deal = quote_first.built.deal
    found = summary.facts([deal.id])[deal.id]
    packet = Document.objects.get(deal=deal, kind='renewal')
    assert found['quotes'] == found['plans'] == 12 and found['last_quote_at']
    assert found['unread'] == [packet.id] and [doc['id'] for doc in found['quote_documents']] == [packet.id]
    assert (found['unpriced'], found['unpriced_lines']) == (0, [])


def test_I50_F88_GD3_two_current_plans_leave_plans_with_no_enrollment(quote_first):
    deal = quote_first.arrive('D').arrive('F').built.deal
    found = summary.facts([deal.id])[deal.id]
    assert found['unpriced'] > 0 and found['unpriced_lines'] == ['medical']
    quote_first.split()
    assert summary.facts([deal.id])[deal.id]['unpriced'] < found['unpriced']


def test_I53_a_plan_that_cites_a_file_reads_it(user, quote_first):
    deal = quote_first.built.deal
    packet = Document.objects.get(deal=deal, kind='renewal')
    plan = services.create_plan(user, deal, line='medical', role='current', carrier='Florida Blue', name='BlueOptions',
                                values={})  # fmt: skip
    type(plan).objects.filter(pk=plan.pk).update(source_document=packet)
    assert summary.facts([deal.id])[deal.id]['unread'] == []


def test_I55_I63_flagged_values_and_sold_lines(user):
    deal = make_deal(user)
    other = make_deal(user, name='Other Co.')
    blank = services.create_plan(user, deal, line='medical', role='alternate', carrier='Cigna', name='Open Access',
                                 values={'plan_type': 'PPO'})  # fmt: skip
    services.create_plan(user, deal, line='dental', role='current', carrier='Delta Dental', name='PPO', values={})
    services.set_sold(user, blank.id, True)
    found = summary.facts([deal.id, other.id, 10**9])
    assert set(found) == {deal.id, other.id}
    assert found[deal.id]['flagged'] > 0 and found[deal.id]['sold_lines'] == ['medical']
    assert found[deal.id]['quotes'] == 1 and found[deal.id]['plans'] == 2
    assert found[other.id]['plans'] == 0 and found[other.id]['flagged'] == 0 and found[other.id]['unread'] == []
