"""Marks (I15–I26; I.6 `test_marks`): Later holds a step until its day, at 21:00 Eastern too (Q.3 #7); each refusal
and its sentence; Done anyway lapses when the step's state, words or items change; marks are firm-wide; an unchanged
write records nothing."""

from datetime import date, datetime, timedelta
from unittest import mock
from zoneinfo import ZoneInfo

import pytest

from agenda import marks, selectors, services
from agenda.models import StepMark
from conftest import make_deal
from deals import activity, clock
from deals.models import Activity, Note
from deals.services import mark_lost

pytestmark = pytest.mark.django_db
EASTERN = ZoneInfo('America/New_York')


def at_eastern(day, hour):
    return mock.patch.object(clock, 'now', return_value=datetime(day.year, day.month, day.day, hour, tzinfo=EASTERN))


def step_of(deal, key, viewer):
    return next((row for row in selectors.deal_agenda(deal, viewer)['rows'] if row.get('key') == key), None)


def test_I16_later_holds_a_step_until_its_day_and_it_comes_back_on_that_day(user, deal):
    day = date(2026, 11, 12)
    with at_eastern(day, 10):
        services.set_later(user, deal.id, 'import_census', '2026-11-14')
    for when, section in ((date(2026, 11, 13), 'later'), (date(2026, 11, 14), 'up_next')):
        with at_eastern(when, 10):
            assert step_of(deal, 'import_census', user)['section'] == section


def test_I15_later_at_21_00_eastern_counts_from_the_agencys_today(user, deal):
    """At 21:00 Eastern UTC is already tomorrow: "Tomorrow" is the agency's tomorrow, and still allowed."""
    evening = date(2026, 11, 12)
    with at_eastern(evening, 21):
        assert clock.now().astimezone(ZoneInfo('UTC')).date() == evening + timedelta(days=1)
        services.set_later(user, deal.id, 'import_census', (evening + timedelta(days=1)).isoformat())
        assert step_of(deal, 'import_census', user)['section'] == 'later'
        with pytest.raises(Exception) as refused:
            services.set_later(user, deal.id, 'complete_intake', evening.isoformat())
        assert 'Pick a day after today' in str(refused.value.detail)


@pytest.mark.parametrize(
    ('key', 'kind', 'until', 'status', 'sentence'),
    [
        ('import_census', 'soon', None, 400, marks.KIND),
        ('import_census', 'later', 'not a day', 400, marks.PICK_A_DAY),
        ('follow_up_client', 'done', None, 400, marks.FOLLOW_UP),
        ('send_drafts', 'done', None, 400, marks.FOLLOW_UP),
        ('read_quotes', 'later', '2099-01-01', 409, 'That step is blocked: there is nothing to mark.'),
        ('no_such_step', 'done', None, 409, marks.GONE),
    ],
)
def test_I17_each_refusal_and_its_sentence(api, deal, key, kind, until, status, sentence):
    body = {'step_key': key, 'kind': kind, **({'until': until} if until else {})}
    response = api.post(f'/api/deals/{deal.id}/agenda/marks/', body, format='json')
    assert response.status_code == status
    assert sentence in str(response.json())


def test_I17_a_lost_deal_refuses_marks(api, user, deal):
    mark_lost(user, deal.id, 'Went with another broker')
    response = api.post(f'/api/deals/{deal.id}/agenda/marks/', {'step_key': 'x', 'kind': 'done'}, format='json')
    assert response.status_code == 409 and response.json()['detail'] == marks.LOST


def test_I21_done_anyway_lapses_when_the_step_changes(user, deal):
    services.set_done_anyway(user, deal.id, 'complete_intake')
    assert step_of(deal, 'complete_intake', user)['state'] == 'done'
    from intake import services as intake_services

    intake_services.update_answers(user, deal.id, {'legal_name': 'Example Co. LLC'})  # one fewer required item
    found = step_of(deal, 'complete_intake', user)
    assert found['state'] == 'open' and 'done_anyway' not in found


def test_I21_the_signature_holds_the_items_behind_a_count():
    step = {'state': 'open', 'label': 'Read carrier quotes', 'basis': [4, 5]}
    assert marks.sig(step) == marks.sig({**step, 'basis': [4, 5]})
    assert marks.sig(step) != marks.sig({**step, 'basis': [4, 6]})


def test_OQ92_marks_are_firm_wide(user, admin_user, deal):
    services.set_later(user, deal.id, 'import_census', (clock.today() + timedelta(days=3)).isoformat())
    assert step_of(deal, 'import_census', admin_user)['later']['by'] == 'Dana'
    assert step_of(deal, 'import_census', admin_user)['section'] == 'later'


def test_I23_one_kind_per_step_and_an_unchanged_write_records_nothing(user, deal):
    until = (clock.today() + timedelta(days=2)).isoformat()
    services.set_later(user, deal.id, 'import_census', until)
    count = Activity.objects.filter(deal=deal, area='agenda').count()
    services.set_later(user, deal.id, 'import_census', until)
    assert Activity.objects.filter(deal=deal, area='agenda').count() == count
    services.set_done_anyway(user, deal.id, 'import_census')
    assert list(StepMark.objects.filter(deal=deal).values_list('kind', flat=True)) == ['done']


def test_I18_a_later_note_stays_on_the_mark_and_on_the_deal_in_one_transaction(user, deal):
    until = clock.today() + timedelta(days=3)
    services.set_later(user, deal.id, 'import_census', until.isoformat(), 'Client is on holiday')
    assert step_of(deal, 'import_census', user)['later']['note'] == 'Client is on holiday'
    note = Note.objects.get(deal=deal)
    assert note.body.startswith('Back to “Import the census” on ') and note.body.endswith(': Client is on holiday')
    row = Activity.objects.filter(deal=deal, area='agenda').latest('id')
    assert 'holiday' not in row.summary and 'holiday' not in str(row.changes)
    assert row.summary.startswith('Later: Import the census (back ')


def test_I22_bring_back_and_undo_clear_the_mark_and_revert_puts_it_back(user, deal):
    until = (clock.today() + timedelta(days=2)).isoformat()
    services.set_later(user, deal.id, 'import_census', until)
    answer = services.clear_mark(user, deal.id, 'import_census')
    assert answer['step']['section'] == 'up_next'
    cleared = Activity.objects.filter(deal=deal, area='agenda').latest('id')
    assert cleared.summary == 'Brought back: Import the census'
    activity.revert(cleared.id, user)
    assert StepMark.objects.get(deal=deal, step_key='import_census').until.isoformat() == until
    with pytest.raises(activity.Refused):
        services.clear_mark(user, make_deal(user, name='Other Co.').id, 'import_census')
