"""`GET deals/{id}/overview/`'s slice-63 blocks on factory and golden deals (plan.md §8.6; M42–M81; Q.9 row 63): Card 1
and Card 2 on a quote-first deal, the enrollment check, Coverage notes, the commission card, the outreach strip and
"Who we've asked". Synthetic only; the module-scoped golden deals are only read."""

import pytest

from deals.services import create_contact, mark_lost
from intake import services as intake_services
from overview import rules
from review import services as review_services

pytestmark = pytest.mark.django_db

ASK = {'asks': {'intake': {'scope': 'missing', 'blocks': ['bor']}, 'census': {'file': True}}}


def overview(api, deal):
    response = api.get(f'/api/deals/{deal.id}/overview/')
    assert response.status_code == 200, response.content
    return response.json()


def group(payload, key):
    return next(found for found in payload['get_to_market']['groups'] if found['key'] == key)


def test_M62_card_2_says_how_quoting_stands_in_the_old_words():
    quotes = {'quotes': 6, 'to_review': 2, 'required_missing': 1, 'sold_lines': []}
    found = {row['key']: row for row in rules.quote_to_close(quotes, None, None)}
    assert list(found) == ['quotes_in', 'built', 'issued', 'sold', 'commission']
    assert found['quotes_in']['detail'] == '6 plans · 2 to review · 1 missing'
    assert found['issued'] == {'key': 'issued', 'detail': '', 'at': None}
    assert found['commission']['detail'] == 'Unlocks once a plan is sold'
    assert rules.quote_to_close({'quotes': 0}, None, None)[0]['detail'] == 'Waiting on carrier responses'
    assert rules.quote_to_close({'quotes': 1}, None, None)[0]['detail'].startswith('1 plan ·')
    sold = {row['key']: row for row in rules.quote_to_close({'quotes': 3, 'sold_lines': ['medical']}, 'T', {})}
    assert sold['issued'] == {'key': 'issued', 'detail': 'Proposal issued', 'at': 'T'}  # C22
    assert sold['commission']['detail'] == 'Book it on the Commission tab'
    booked = rules.quote_to_close({'quotes': 3, 'sold_lines': ['medical']}, None, {'state': 'booked'})
    assert booked[-1]['detail'] == 'Booked at sale'


def test_Q9_63_GD3_quote_first_shows_its_quotes_on_card_2_and_says_intake_still_applies(api, gd3):
    payload = overview(api, gd3.deal)
    quotes = [plan for plan in gd3.spec['plans'] if plan['role'] in ('renewal', 'alternate')]
    assert payload['quote_to_close'][0]['detail'].startswith(f'{len(quotes)} plans ·')
    card = payload['get_to_market']
    assert (
        card['badge'] == 'blocked'
        and card['quotes_first'] == 'Quotes came in first — intake, census and the RFP still apply'
    )
    assert card['headcount']['from'] == 'advisor' and card['headcount']['value']
    census = group(payload, 'census')
    assert census['employees'] == 0 and census['typed_counts']  # M110: priced from typed counts, no census yet
    assert census['ask'] == 'file'
    assert 'skipped' not in str(payload['get_to_market'])  # M40: nothing reads "skipped"


def test_M67_the_census_group_names_the_three_enrolled_counts_when_they_differ(api, user, quote_first):
    deal = quote_first.built.deal
    before = overview(api, deal)
    assert before['enrollment_check']['differ'] is False and group(before, 'census')['enrollment_warning'] is None
    advisor = before['enrollment_check']['advisor']
    intake_services.update_answers(user, deal.id, {'enrolled_count': str(advisor + 7)})
    after = overview(api, deal)
    check = after['enrollment_check']
    assert (check['intake'], check['advisor'], check['differ']) == (advisor + 7, advisor, True)
    assert group(after, 'census')['enrollment_warning'] == check['warning']
    assert f'intake {advisor + 7}' in check['warning'] and f'Advisor {advisor}' in check['warning']


def test_M80_coverage_notes_list_each_line_that_carries_a_note(api, user, deal):
    assert overview(api, deal)['coverage_notes'] == []
    intake_services.create_coverage(
        user, deal.id, {'line': 'medical', 'carrier': 'Example Health', 'in_force': True, 'notes': ' Renews in July. '}
    )
    intake_services.create_coverage(user, deal.id, {'line': 'dental', 'in_force': True, 'notes': ''})
    notes = overview(api, deal)['coverage_notes']
    assert [(row['line'], row['carrier'], row['body']) for row in notes] == [
        ('medical', 'Example Health', 'Renews in July.')
    ]
    assert notes[0]['label'] == 'Medical'


def test_M81_the_commission_block_is_the_commission_tabs_card(api, gd1_sold):
    payload = overview(api, gd1_sold.deal)
    card = payload['commission']
    assert set(card) >= {'expected', 'note', 'chips', 'booking'}
    assert card['booking']['state'] == 'booked' and card['booking']['record_count'] > 0
    assert payload['tiles']['expected_revenue'] is not None
    assert payload['quote_to_close'][-1]['detail'] == 'Booked at sale'


def test_M68_M69_outreach_counts_asks_per_request_and_lists_who_we_asked(api, user, deal):
    empty = overview(api, deal)['outreach']
    assert (empty['open'], empty['links'], empty['last_response_at']) == (0, [], None)
    hr = create_contact(user, deal.client_id, role='hr_admin', name='Casey HR (synthetic)', email='casey@example.com')
    payroll = create_contact(user, deal.client_id, role='payroll_contact', name='Pat Payroll (synthetic)')
    create_contact(user, deal.client_id, role='prior_broker', name='Prior Broker (synthetic)')
    made = review_services.create(
        user, deal.id, {**ASK, 'people': [{'contact_id': hr.id}, {'name': 'Riley (synthetic)'}]}
    )
    draft = overview(api, deal)['outreach']
    assert draft['open'] == 0 and draft['links_total'] == 2  # a draft is no ask yet
    assert {row['state'] for row in draft['links']} == {'draft'}
    for link, _path, _pin in made.links:
        review_services.mark_sent(user, link.id, copied=True)
    found = overview(api, deal)['outreach']
    assert (found['open'], found['waiting'], found['oldest_days']) == (1, 1, 0)  # one request to two people: one ask
    first = next(row for row in found['links'] if row['name'] == 'Casey HR (synthetic)')
    assert first['role'] == 'HR Admin' and first['shared'] is True
    assert (first['state'], first['state_label']) == ('waiting', 'Waiting') and first['days_left'] > 0
    assert first['asks'] and found['last_contact_at'] is not None
    assert found['never_asked'] == [payroll.name]  # client-side contacts only, never the prior broker


def test_M49_a_lost_deal_closes_its_asks_and_says_why(api, user, deal):
    assert overview(api, deal)['asks'] == {'refusal': None, 'file_asks_ready': True}
    mark_lost(user, deal.id, 'Went elsewhere (synthetic)')
    payload = overview(api, deal)
    assert payload['asks']['refusal'] and group(payload, 'census')['ask'] is None
