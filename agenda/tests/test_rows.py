"""What the marked steps say (I67, I69, I119–I121; I.6 `test_rows`): the next step, finished, the banner, the journey
and progress, all from the same steps (pure)."""

from datetime import date

from agenda import journey, marks, rows
from agenda.steps import steps

from .helpers import NOW, TODAY, ask, at, facts, quotes_in, review_with

CENSUS_ASK = {'census': {'scope': 'none', 'file': True}}


def marked(found, marks_by_key):
    return marks.apply_marks(steps(found, TODAY, NOW), marks_by_key, TODAY)


def later(until, key='x'):
    return {'kind': 'later', 'until': until, 'sig': '', 'note': '', 'by': 'Dana', 'at': None}


def done_anyway(step):
    return {'kind': 'done', 'until': None, 'sig': marks.sig(step), 'note': '', 'by': 'Dana', 'at': None}


def test_I67_the_next_step_is_the_first_live_lead_step():
    found = steps(facts(quotes=quotes_in(unread=[3])), TODAY, NOW)
    assert rows.next_step(found)['key'] == 'read_quotes'


def test_I67_later_on_the_lead_step_moves_the_next_step_on():
    found = facts(quotes=quotes_in(unread=[3]))
    held = marked(found, {'read_quotes': later(date(2026, 11, 20))})
    assert rows.next_step(held)['key'] == 'build_proposal'


def test_I67_every_lead_step_held_keeps_the_earliest_later_day():
    found = facts(deal={'stage': 'sold', 'sold': True}, quotes=quotes_in(sold_lines=['medical']),
                  commission={'unrated': ['medical']})  # fmt: skip
    held = marked(found, {'commission': later(date(2026, 11, 25))})
    step = rows.next_step(held)
    assert step['key'] == 'commission' and step['later_until'] == '2026-11-25'


def test_I121_done_anyway_on_the_only_lead_step_never_makes_a_deal_finished():
    found = facts(deal={'stage': 'sold', 'sold': True}, quotes=quotes_in(sold_lines=['medical']),
                  commission={'unrated': ['medical']})  # fmt: skip
    unmarked = steps(found, TODAY, NOW)
    commission = next(step for step in unmarked if step['key'] == 'commission')
    after = marks.apply_marks(unmarked, {'commission': done_anyway(commission)}, TODAY)
    assert not rows.finished(unmarked)
    step = rows.next_step(after)
    assert step['key'] == 'commission' and step['done_anyway'] is True


def test_I121_a_sold_deal_with_everything_entered_is_finished():
    found = facts(deal={'stage': 'sold', 'sold': True}, quotes=quotes_in(sold_lines=['medical']))
    assert rows.finished(steps(found, TODAY, NOW))


def test_I119_the_banner_names_who_we_wait_on_from_the_same_steps():
    found = steps(facts(review=review_with(ask(1, CENSUS_ASK, sent_days_ago=2))), TODAY, NOW)
    banner = rows.waiting(found, TODAY)
    assert banner['state'] == 'waiting' and banner['key'] == 'import_census'
    assert banner['owner_words'] == 'the client'
    assert banner['label'] == 'Waiting on the client for the census'
    with_us = rows.waiting(steps(facts(quotes=quotes_in(unread=[2])), TODAY, NOW), TODAY)
    assert with_us == {'state': 'with_us', 'label': 'The ball is in our court', 'next': 'Read carrier quotes'}


def test_I119_carriers_owe_us_since_the_deal_went_to_market():
    found = steps(facts(intake={'ready_state': 'submitted', 'marketed_at': at(11)}), TODAY, NOW)
    banner = rows.waiting(found, TODAY)
    assert banner['owner'] == 'carrier' and banner['days'] == 11 and banner['severity'] == 'warn'


def test_I69_progress_skips_the_milestones_a_quote_first_deal_skipped():
    quote_first = facts(quotes=quotes_in())
    milestones = journey.journey(quote_first, steps(quote_first, TODAY, NOW))
    states = {row['key']: row['state'] for row in milestones}
    assert states['intake_ready'] == 'skipped' and states['marketed'] == 'skipped'
    assert states['quotes_in'] == 'done' and states['enrollment_in'] == 'done'
    assert journey.progress(milestones) == {'done': 2, 'total': 6, 'pct': 33}
    fresh = facts()
    counted = journey.progress(journey.journey(fresh, steps(fresh, TODAY, NOW)))
    assert counted == {'done': 0, 'total': 8, 'pct': 0}


def test_I120_the_journey_marks_the_first_milestone_still_to_do():
    found = facts(intake={'ready_state': 'ready'})
    milestones = journey.journey(found, steps(found, TODAY, NOW))
    current = [row['key'] for row in milestones if row['current']]
    assert current == ['enrollment_in']
    assert [row['group'] for row in milestones][:3] == ['get_to_market'] * 3


def test_I4_sections():
    found = facts(review=review_with(ask(1, CENSUS_ASK, sent_days_ago=1)), quotes=quotes_in(unread=[1]))
    held = marked(found, {'read_quotes': later(date(2026, 11, 20))})
    sections = {step['key']: rows.section(step) for step in held}
    assert sections['import_census'] == 'waiting'
    assert sections['read_quotes'] == 'later'
    assert sections['build_proposal'] == 'up_next'
    assert sections['issue_proposal'] == 'blocked'
