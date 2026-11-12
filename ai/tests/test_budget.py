"""Pricing, the caps and the call ledger (plan.md §10.3; D8, D53, D99, D100, D24; slice 18)."""

from decimal import Decimal

import pytest

from ai import budget, pricing
from ai.models import Call, DealAi, Job


def test_D53_a_call_is_priced_from_the_model_that_answered():
    usage = {
        'input_tokens': 1_000_000,
        'output_tokens': 1_000_000,
        'cache_read_input_tokens': 1_000_000,
        'cache_creation_input_tokens': 1_000_000,
    }
    assert pricing.cost(pricing.SONNET, usage) == Decimal('2') + Decimal('10') + Decimal('0.10') + Decimal('2.5')
    assert pricing.cost(pricing.OPUS, usage) == Decimal('4') + Decimal('20') + Decimal('0.20') + Decimal('5')
    assert pricing.cost('claude-unknown-9', {'output_tokens': 1_000_000}) == Decimal('20')  # the top price


def test_D53_haiku_prices_a_prompt_past_100k_tokens_at_its_higher_tier():
    small = pricing.cost(pricing.HAIKU, {'input_tokens': 100_000, 'output_tokens': 0})
    large = pricing.cost(pricing.HAIKU, {'input_tokens': 100_001, 'output_tokens': 0})
    assert small == Decimal('0.01') and large > Decimal('0.05')


def test_D53_the_worst_case_is_the_whole_input_and_every_output_token():
    assert pricing.worst_case(pricing.SONNET, 10_000, 128_000) == Decimal('0.02') + Decimal('1.28')


def test_D53_total_cap_refuses_a_call_that_could_pass_it(db, settings):
    settings.AI_TOTAL_BUDGET_USD = '1.50'
    Call.objects.create(purpose='read', model=pricing.SONNET, status=Call.DONE, cost_usd=Decimal('0.25'))
    with pytest.raises(budget.OverLimit) as refused:
        budget.reserve(model=pricing.SONNET, input_tokens=10_000, max_tokens=128_000, purpose='read')
    assert refused.value.kind == budget.TOTAL and '$1.50' in refused.value.sentence
    assert Call.objects.count() == 1  # nothing reserved, nothing sent
    small = budget.reserve(model=pricing.SONNET, input_tokens=10_000, max_tokens=64_000, purpose='read')
    assert small.status == Call.PENDING and small.estimate_usd == Decimal('0.6600')


def test_D53_a_call_out_counts_at_its_worst_case_until_settled(db, settings):
    settings.AI_TOTAL_BUDGET_USD = ''
    row = budget.reserve(model=pricing.SONNET, input_tokens=1000, max_tokens=1000, purpose='eval')
    assert budget.total_spent() == row.estimate_usd
    cost = budget.settle(
        row, answered=pricing.OPUS, usage={'input_tokens': 1000, 'output_tokens': 10}, status=Call.DONE
    )
    row.refresh_from_db()
    assert cost == Decimal('0.004200') and row.answered == pricing.OPUS and budget.total_spent() == cost


def test_D53_no_cap_when_the_setting_is_unset(db, settings):
    settings.AI_TOTAL_BUDGET_USD = ''
    Call.objects.create(purpose='read', model=pricing.SONNET, status=Call.DONE, cost_usd=Decimal('999'))
    assert budget.total_cap() is None
    assert budget.reserve(model=pricing.SONNET, input_tokens=1, max_tokens=1, purpose='read').pk


def test_D8_settling_adds_the_cost_to_its_job(user, deal):
    job = Job.objects.create(deal=deal, lane='work', kind='read', created_by=user)
    row = budget.reserve(model=pricing.SONNET, input_tokens=10, max_tokens=10, purpose='read', job=job)
    budget.settle(row, answered=pricing.SONNET, usage={'output_tokens': 100_000}, status=Call.DONE)
    job.refresh_from_db()
    assert job.cost_usd == Decimal('1') and budget.deal_spent(deal.id) == Decimal('1')
    assert row.deal_id == deal.id


def test_D24_D53_a_run_over_its_cap_waits_unless_run_anyway(deal, settings):
    settings.AI_READ_LIMIT_USD = '3'
    with pytest.raises(budget.OverLimit) as waits:
        budget.check_run(deal.id, Decimal('3.50'))
    assert waits.value.kind == budget.RUN and 'run it anyway' in waits.value.sentence
    budget.check_run(deal.id, Decimal('3.50'), override=True)
    budget.check_run(deal.id, Decimal('2.99'))


def test_D99_D100_a_deal_budget_counts_its_jobs_and_its_own_figure_wins(user, deal, settings):
    settings.AI_DEAL_BUDGET_USD = '25'
    Job.objects.create(deal=deal, lane='work', kind='read', created_by=user, cost_usd=Decimal('24'))
    with pytest.raises(budget.OverLimit) as waits:
        budget.check_run(deal.id, Decimal('2'))
    assert waits.value.kind == budget.DEAL
    DealAi.objects.create(deal=deal, budget_usd=Decimal('40'))
    budget.check_run(deal.id, Decimal('2'))


def test_D53_a_read_is_estimated_from_its_pages_without_a_call():
    from ai import ranges

    parts = [ranges.Range('pdf', pages=(1, 2), est_input=4000, est_output=2000)]
    one = budget.run_estimate(pricing.SONNET, parts, 3000)
    two = budget.run_estimate(pricing.SONNET, parts * 2, 3000)
    assert Decimal('0') < one < two < Decimal('1')
