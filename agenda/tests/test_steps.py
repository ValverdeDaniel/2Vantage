"""The step table (plan.md §5.9; I41–I66; Q.9 row 60 "the steps() table; quote-first leads; carrier wait from
marketed_at; the commission step"), table-driven over facts dicts: the pure `steps(facts, today, now)`."""

from datetime import timedelta

import pytest

from agenda.steps import steps

from .helpers import BOR_ASK, CENSUS_ASK, FORM_ASK, NOW, TODAY, ask, at, by_key, facts, quotes_in, review_with


def run(found):
    return by_key(steps(found, TODAY, NOW))


def blocked_by(*blockers, items=()):
    return {'blockers': [{'kind': k, 'key': key, 'label': label} for k, key, label in blockers], 'items': list(items)}


def item(key, satisfy='document', status='missing', **more):
    return {'key': key, 'label': key.replace('_', ' ').title(), 'satisfy': satisfy, 'status': status, 'kind': '',
            **more}  # fmt: skip


def test_I66_a_lost_deal_has_no_steps():
    assert steps(facts(deal={'lost': True, 'stage': 'lost'}), TODAY, NOW) == []


def test_I44_each_intake_blocker_is_one_step_in_the_old_words():
    intake = blocked_by(
        ('question', 'fein', 'FEIN'),
        ('question', 'legal_name', 'Legal Company Name'),
        ('contacts', 'contacts', 'HR contact'),
        ('bor', 'bor', 'Signed BOR'),
        ('census', 'census', 'Census'),
        ('to_check', 'sic', 'SIC (to check)'),
        items=[
            item('coverage_intent', 'auto'),
            item('cobra', 'attest', label='COBRA participants'),
            item('invoice', kind='invoice'),
            item('renewal', kind='renewal'),
            item('census', 'auto'),
        ],
    )
    found = run(facts(intake=intake))
    assert found['complete_intake']['label'] == 'Complete intake — 2 required items'
    assert found['checklist:coverage_intent']['label'] == 'Confirm the coverage and what we are shopping'
    assert found['checklist:cobra']['label'] == 'Checklist: COBRA participants'
    assert found['checklist_ask']['label'] == 'Ask the client for 2 checklist items'  # census has its own step
    assert found['review_flagged_answers']['label'] == 'Review 1 flagged answer'
    assert found['add_hr_contact']['label'] == "Add the client's HR contact"
    assert found['get_bor']['label'] == 'Get the broker of record letter signed'
    assert 'finish_intake' not in found
    assert all(found[key]['lead'] for key in ('complete_intake', 'add_hr_contact', 'get_bor'))


def test_I44_finish_intake_covers_only_blockers_with_no_step_of_their_own():
    found = run(facts(intake=blocked_by(('question', 'fein', 'FEIN'), ('unsure', 'x', 'An unsure answer'))))
    assert found['finish_intake']['label'] == 'Finish intake — An unsure answer'
    assert run(facts(intake=blocked_by(('question', 'fein', 'FEIN')))).get('finish_intake') is None


@pytest.mark.parametrize(
    ('asks', 'state'),
    [
        ((), 'open'),
        ((ask(1, BOR_ASK),), 'waiting'),
        ((ask(1, CENSUS_ASK),), 'open'),  # an ask out, but not for the BOR (I.5 bug 6)
        ((ask(1, BOR_ASK, state='draft'),), 'open'),  # a draft nobody sent waits on us
    ],
)
def test_I45_waiting_on_the_client_only_when_an_ask_out_asked_for_it(asks, state):
    found = run(facts(intake=blocked_by(('bor', 'bor', 'Signed BOR')), review=review_with(*asks)))
    assert found['get_bor']['state'] == state
    if state == 'waiting':
        assert found['get_bor']['owner'] == 'client'
        assert found['get_bor']['label'] == 'Waiting on the client to sign the broker of record letter'


def test_I45_checklist_files_wait_only_when_their_kind_was_asked():
    intake = blocked_by(items=[item('invoice', kind='invoice')])
    asked = {'documents': {'slots': ['invoice@medical'], 'missing': False}}
    assert run(facts(intake=intake, review=review_with(ask(1, asked))))['checklist_ask']['state'] == 'waiting'
    other = {'documents': {'slots': ['claims'], 'missing': False}}
    assert run(facts(intake=intake, review=review_with(ask(1, other))))['checklist_ask']['state'] == 'open'


@pytest.mark.parametrize(
    ('row', 'files', 'asks', 'label', 'state'),
    [
        ({'status': 'missing', 'form_key': 'florida_blue_51'}, [], (), 'Send the medical questionnaire', 'open'),
        ({'status': 'missing', 'form_key': ''}, [], (ask(1, FORM_ASK),),
         'Waiting on the client for the medical questionnaire', 'waiting'),
        ({'status': 'done', 'has_document': True}, [{'id': 9, 'review_state': ''}], (),
         'Review the returned medical questionnaire', 'open'),
        ({'status': 'done', 'has_document': True}, [{'id': 9, 'review_state': 'accepted'}], (),
         'Medical questionnaire on file', 'done'),
        ({'status': 'done', 'signed': True}, [], (), 'Medical questionnaire signed', 'done'),
    ],
)  # fmt: skip
def test_I46_the_questionnaire_has_its_own_step(row, files, asks, label, state):
    intake = blocked_by(items=[item('medical_questionnaire', kind='questionnaire', **row)])
    found = run(facts(intake=intake, documents={'questionnaire_files': files}, review=review_with(*asks)))
    assert (found['questionnaire']['label'], found['questionnaire']['state']) == (label, state)
    assert 'checklist_ask' not in found  # never counted twice


def test_I46_a_waived_questionnaire_has_no_step():
    intake = blocked_by(items=[item('medical_questionnaire', status='waived')])
    assert 'questionnaire' not in run(facts(intake=intake))


def test_I47_ready_intake_leads_to_market_and_marketed_reads_sent_to_market():
    ready = run(facts(intake={'ready_state': 'ready'}))
    assert ready['send_rfp']['label'] == 'Intake ready — market for quotes' and ready['send_rfp']['lead']
    sent = run(facts(intake={'ready_state': 'submitted', 'marketed_at': at(2)}))
    assert sent['send_rfp']['label'] == 'Sent to market' and sent['send_rfp']['state'] == 'done'
    assert 'build_rfp' not in sent


def test_I48_build_rfp_counts_its_cards_and_never_leads():
    found = run(facts(rfp={'cards_done': 2, 'cards_total': 5}))
    assert found['build_rfp']['label'] == 'Build the RFP — 2 of 5 cards completed'
    assert not found['build_rfp']['lead']
    assert run(facts(rfp={'cards_done': 5, 'cards_total': 5}))['build_rfp']['state'] == 'done'


def test_OQ90_intake_questionnaire_and_rfp_steps_stop_leading_once_quotes_are_in():
    intake = blocked_by(('question', 'fein', 'FEIN'), items=[item('medical_questionnaire', form_key='x')])
    before = run(facts(intake=intake))
    after = run(facts(intake=intake, quotes=quotes_in()))
    assert before['complete_intake']['lead'] and before['questionnaire']['lead']
    assert not after['complete_intake']['lead'] and not after['questionnaire']['lead']
    assert after['complete_intake']['state'] == 'open'  # still listed


def test_I50_import_the_census_leads_until_typed_counts_price_every_plan():
    assert run(facts())['import_census']['lead']
    typed = run(facts(quotes=quotes_in()))['import_census']
    assert typed['label'] == 'Import the census' and not typed['lead']


def test_I50_quotes_in_with_no_enrollment_source_the_step_leads_as_add_the_census_or_type_enrollment():
    found = run(facts(quotes=quotes_in(unpriced=4, unpriced_lines=['medical'])))['import_census']
    assert found['label'] == 'Add the census, or type enrollment in the Advisor'
    assert found['lead'] and found['tab'] == 'advisor' and found['params'] == {'line': 'medical'}
    assert found['also'] == {'tab': 'census', 'label': 'Census ▸'}


def test_I50_waiting_on_the_client_for_the_census_when_an_ask_out_named_it():
    found = run(facts(review=review_with(ask(1, CENSUS_ASK))))['import_census']
    assert (found['label'], found['state'], found['owner']) == ('Waiting on the client for the census', 'waiting',
                                                                 'client')  # fmt: skip


def test_I49_a_census_that_arrives_late_makes_mapping_lead_even_with_typed_counts():
    file_in = run(facts(quotes=quotes_in(), census={'files': 1}))
    assert file_in['map_census']['lead'] and 'import_census' not in file_in
    mapped = run(facts(quotes=quotes_in(), census={'files': 1, 'proposed_import': 7}))
    assert mapped['review_mapping']['lead'] and mapped['review_mapping']['params'] == {'import': 7}


def test_I51_census_errors_client_values_and_questions():
    found = run(
        facts(
            census={'employees': 12, 'errors': 3},
            review={'pending': {'census': 2, 'people': 1, 'intake': 0}, 'questions': {'open': 2, 'oldest_at': at(1)}},
        )
    )
    assert found['fix_census']['label'] == 'Fix 3 census errors' and found['fix_census']['severity'] == 'error'
    assert found['approve_client']['label'] == 'Review 3 client-provided values'
    assert found['approve_client']['params'] == {'view': 'queue', 'section': 'census'}
    assert found['answer_client_questions']['label'] == 'Answer 2 questions from the client'
    assert not found['answer_client_questions']['lead'] and 'import_census' not in found


def test_I53_reading_quotes_open_blocked_or_waiting():
    unread = run(facts(quotes=quotes_in(unread=[4, 5])))['read_quotes']
    assert (unread['label'], unread['state'], unread['basis']) == ('Read carrier quotes', 'open', [4, 5])
    blocked = run(facts())['read_quotes']
    assert blocked['state'] == 'blocked' and blocked['blocked_reason'] == 'After the RFP goes to market'
    outside = run(facts(deal={'stage': 'quoting'}))['read_quotes']
    assert (outside['label'], outside['state'], outside['owner']) == ('Waiting on carrier quotes', 'waiting',
                                                                     'carrier')  # fmt: skip
    assert 'read_quotes' not in run(facts(quotes=quotes_in()))


@pytest.mark.parametrize(('days', 'follow_up'), [(9, False), (10, True), (14, True)])
def test_I54_the_carrier_wait_counts_from_marketed_at_even_after_an_example_quote(days, follow_up):
    marketed = {'ready_state': 'submitted', 'marketed_at': at(days)}
    example = quotes_in(1, last_quote_at=at(days + 5))  # read before the deal went to market
    found = run(facts(intake=marketed, quotes=example))
    assert found['read_quotes']['state'] == 'waiting' and found['read_quotes']['since'] == at(days)
    assert ('follow_up_carriers' in found) == follow_up
    if follow_up:
        step = found['follow_up_carriers']
        assert step['label'] == f'Follow up with the carriers — at market {days} days, no quotes back'
        assert step['due'] == (TODAY - timedelta(days=days) + timedelta(days=10)).isoformat()
        assert step['wait_days'] == 10


def test_I54_a_quote_that_arrived_after_marketing_ends_the_wait():
    marketed = {'ready_state': 'submitted', 'marketed_at': at(12)}
    found = run(facts(intake=marketed, quotes=quotes_in(2, last_quote_at=at(3))))
    assert 'read_quotes' not in found and 'follow_up_carriers' not in found


def test_I55_flagged_values():
    found = run(facts(quotes=quotes_in(flagged=6)))['review_values']
    assert found['label'] == 'Review 6 flagged values' and found['lead']


def test_I56_I57_I60_build_issue_and_sell():
    open_build = run(facts(quotes=quotes_in(), proposals={'needs': 3, 'picked': 1}))
    assert open_build['build_proposal']['label'] == 'Build the proposal — 1 of 3 lines recommended'
    assert open_build['issue_proposal']['state'] == 'blocked'
    assert open_build['mark_sold']['blocked_reason'] == 'After the proposal is issued'
    built = run(facts(quotes=quotes_in(), proposals={'needs': 3, 'picked': 3, 'ready': True}))
    assert built['build_proposal']['state'] == 'done' and built['issue_proposal']['state'] == 'open'
    issued = run(facts(quotes=quotes_in(), proposals={'latest': {'version': 2, 'issued_at': at(1)}}))
    assert issued['issue_proposal']['label'] == 'Proposal issued (v2)' and issued['issue_proposal']['state'] == 'done'
    assert issued['mark_sold']['state'] == 'open' and issued['mark_sold']['label'] == 'Mark the winning plan sold'
    none = run(facts())
    assert none['mark_sold']['blocked_reason'] == 'After the carrier quotes are in'


@pytest.mark.parametrize(('days', 'state'), [(6, 'waiting'), (7, 'open'), (9, 'open')])
def test_I58_the_proposal_follow_up_opens_at_exactly_seven_days(days, state):
    issued = {'latest': {'version': 1, 'issued_at': at(days)}}
    found = run(facts(quotes=quotes_in(), proposals=issued))['follow_up_selection']
    assert found['state'] == state
    words = f'issued {days} days ago'
    assert words in found['label']
    if state == 'open':
        assert found['label'] == f'Follow up on the proposal — {words}, nothing sold yet'


def test_I63_after_the_sale_the_commission_step_leads_then_sold():
    sold = {'stage': 'sold', 'sold': True}
    found = run(facts(deal=sold, quotes=quotes_in(sold_lines=['dental', 'medical']),
                      commission={'unrated': ['dental', 'medical']}))  # fmt: skip
    assert found['commission']['label'] == 'Enter the commission for 2 sold lines' and found['commission']['lead']
    assert found['mark_sold']['label'] == 'Sold' and found['mark_sold']['state'] == 'done'
    assert run(facts(deal=sold, quotes=quotes_in()))['commission']['state'] == 'done'


def test_I66_asks_and_census_steps_leave_once_sold():
    sold = facts(deal={'stage': 'sold', 'sold': True}, review=review_with(ask(1, CENSUS_ASK, sent_days_ago=9)))
    found = run(sold)
    assert not {'follow_up_client', 'send_drafts', 'import_census', 'read_quotes', 'complete_intake'} & set(found)


def test_I64_one_drafts_step_across_many_drafts():
    one = run(facts(review=review_with(ask(1, CENSUS_ASK, state='draft'))))
    assert one['send_drafts']['label'] == 'Send the census request you drafted'
    two = run(facts(review=review_with(ask(1, CENSUS_ASK, state='draft'), ask(2, BOR_ASK, state='draft'))))
    assert two['send_drafts']['label'] == 'Send the 2 requests you drafted'


@pytest.mark.parametrize(('days', 'state'), [(2, 'waiting'), (3, 'open')])
def test_I65_one_follow_up_opens_at_exactly_three_days(days, state):
    found = run(facts(review=review_with(ask(1, CENSUS_ASK, sent_days_ago=days))))['follow_up_client']
    assert found['state'] == state
    if state == 'waiting':
        assert found['label'] == f'Waiting on the client: census request sent {days} days ago to Riley Example'
    else:
        assert found['label'] == f'Follow up: census request sent {days} days ago to Riley Example, not returned'
        assert found['due'] == (TODAY - timedelta(days=days) + timedelta(days=3)).isoformat()


def test_I65_many_asks_are_one_follow_up_and_an_expired_one_is_due_at_once():
    asks = (ask(1, CENSUS_ASK, sent_days_ago=1), ask(2, {**BOR_ASK, **CENSUS_ASK}, sent_days_ago=2))
    found = run(facts(review=review_with(*asks, expired=1)))
    assert [key for key in found if key == 'follow_up_client'] == ['follow_up_client']
    assert found['follow_up_client']['label'] == (
        'Follow up: 2 requests out with the client, the oldest sent 2 days ago — 1 expired, send fresh link'
    )
    only = run(facts(review=review_with(expired=2)))['follow_up_client']
    assert only['label'] == 'Follow up: 2 requests expired unanswered — send fresh links' and only['state'] == 'open'


def test_I41_steps_come_in_catalogue_order():
    found = steps(facts(intake=blocked_by(('question', 'fein', 'FEIN')), quotes=quotes_in(unread=[1])), TODAY, NOW)
    keys = [step['key'] for step in found]
    assert keys.index('complete_intake') < keys.index('import_census') < keys.index('read_quotes')
    assert keys.index('read_quotes') < keys.index('build_proposal')
