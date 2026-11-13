"""The Next ranking (plan.md §8.8; L3, L4, L14, L25; B19, Ch. 8): pure, table-driven — the order the Board's Next
banner, a section bar's Next line and the request page's banner share."""

from datetime import UTC, datetime, timedelta

from review.rules import next as next_rules

NOW = datetime(2026, 11, 12, 12, 0, tzinfo=UTC)


def link(days, *, unopened=False, **kw):
    return {'link_id': kw.get('link_id', 1), 'request_id': 9, 'name': kw.get('name', 'Dana'), 'days_left': days,
            'sent': kw.get('sent', True), 'submitted': kw.get('submitted', False), 'expired': False,
            'unopened': unopened}  # fmt: skip


def kinds(entries):
    return [(entry['kind'], entry['label']) for entry in entries]


def test_L4_the_order_of_what_comes_next():
    facts = {
        'links': [link(1, unopened=False, link_id=1, name='Lee'), link(2, unopened=True, link_id=2, name='Dana')],
        'questions': {'census': (2, NOW - timedelta(hours=30)), 'intake': (1, NOW - timedelta(hours=2))},
        'intake_required': 3,
        'census_required': 4,
        'answers': {'intake': (5, NOW - timedelta(days=2))},
        'files': 1,
    }
    found = next_rules.rank(facts, NOW)
    assert kinds(found) == [
        ('link_expiring', 'Dana’s link runs out in 2 days'),
        ('question', '2 client questions on the census'),
        ('blocks_carrier', '3 intake questions required to market'),
        ('blocks_carrier', '4 required census values still blank'),
        ('link_expiring', 'Lee’s link runs out in 1 day'),
        ('question', '1 client question on the intake'),
        ('oldest', '5 answers from the client on the intake'),
        ('oldest', '1 file from the client to check'),
    ]
    assert found[0]['unopened'] and found[0]['link_id'] == 2


def test_B19_once_quotes_are_in_the_intake_drops_below_the_answers():
    facts = {'intake_required': 3, 'answers': {'census': (1, NOW)}, 'quotes_in': True}
    assert [entry['kind'] for entry in next_rules.rank(facts, NOW)] == ['oldest', 'blocks_carrier']


def test_L4_Ch8_quotes_on_typed_counts_with_no_census_lead():
    found = next_rules.rank({'no_census': True, 'quotes_in': True}, NOW)
    assert kinds(found) == [('blocks_carrier', 'No census on file yet')]
    assert next_rules.rank({'no_census': True}, NOW) == []


def test_L4_a_link_that_is_far_off_answered_or_not_sent_is_not_next():
    facts = {'links': [link(5), link(1, submitted=True), link(1, sent=False)]}
    assert next_rules.rank(facts, NOW) == []


def test_L14_a_section_keeps_its_own_part_and_every_link():
    facts = {
        'links': [link(0, unopened=True)],
        'intake_required': 1,
        'census_required': 2,
        'questions': {'documents': (1, NOW)},
        'files': 2,
    }
    census = next_rules.rank(facts, NOW, surface='census')
    assert [entry['kind'] for entry in census] == ['link_expiring', 'blocks_carrier']
    assert census[0]['label'] == 'Dana’s link runs out today'
    intake = next_rules.rank(facts, NOW, surface='intake')
    assert [entry['surface'] for entry in intake] == ['', 'intake', 'intake', 'intake']


def test_L4_at_most_eight():
    facts = {'links': [link(1, link_id=n, name=f'P{n}') for n in range(12)]}
    assert len(next_rules.rank(facts, NOW)) == next_rules.LIMIT


def test_L119_the_predicates_agenda_reads():
    assert next_rules.expiring(link(2)) and not next_rules.expiring(link(3))
    assert next_rules.question_waiting(NOW - timedelta(hours=25), NOW)
    assert not next_rules.question_waiting(NOW - timedelta(hours=23), NOW)
