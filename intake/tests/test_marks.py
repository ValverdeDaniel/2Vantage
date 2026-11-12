"""Review marks on intake answers (plan.md §10.7; B10, B11; E85–E88; OQ28): approve, ignore, needs checking and clear,
by refs or over the shown answers' open warnings; one `marked` Activity row with marks only; Revert once."""

import pytest

from deals import activity
from deals.models import Activity
from intake import flags, services
from intake.models import Intake

pytestmark = pytest.mark.django_db

DOUBTED = {'origin': 'ai', 'doc': 4, 'low': 'two figures on the page'}


@pytest.fixture
def read(deal):
    """An intake with two doubted reads, a clean read, a typed answer and a doubted read on a hidden question."""
    return Intake.objects.create(
        deal=deal,
        answers={'atne': '68', 'dba': 'Ex', 'union': 'No', 'legal_name': 'Example Co.', 'pcori_handler': 'TPA'},
        sources={
            'atne': dict(DOUBTED),
            'dba': dict(DOUBTED),
            'union': {'origin': 'ai', 'doc': 4},
            'legal_name': {'origin': 'typed'},
            'pcori_handler': dict(DOUBTED),  # hidden: pcori_filing is blank
        },
        flags=2,
    )


def _marks(api, deal, **body):
    return api.post(f'/api/deals/{deal.id}/intake/marks/', body, format='json')


def test_B11_the_review_bar_approves_every_open_warning_on_the_form(api, deal, read):
    before = api.get(f'/api/deals/{deal.id}/intake/').json()
    assert before['review'] == {'open': 2, 'check': 0, 'unflagged': 2}
    assert before['status']['atne'] == before['status']['dba'] == 'to_check'
    answer = _marks(api, deal, action='approve').json()
    assert answer['changed'] == 2 and set(answer['sources']) == {'atne', 'dba'}
    assert answer['review'] == {'open': 0, 'check': 0, 'unflagged': 0}
    assert 'to_check' not in answer['status'].values()
    intake = Intake.objects.get(deal=deal)
    assert intake.flags == 0 and flags.rebuild([deal.id]) == []
    assert intake.sources['pcori_handler'] == DOUBTED  # hidden: not on the form, not counted
    assert intake.updated_at == read.updated_at  # marks are bookkeeping
    row = Activity.objects.get(pk=answer['activity_id'])
    assert row.action == 'marked' and row.summary == 'Approved 2 intake answers'
    assert set(row.changes[0]['k']) == {'mark.atne', 'mark.dba'}  # marks only, never the answer


def test_B10_select_fields_flags_exactly_the_ticked_answers(api, user, deal, read):
    answer = _marks(api, deal, action='check', refs=['intake:legal_name', 'intake:fein']).json()
    assert answer['changed'] == 1  # FEIN is blank: a blank takes no mark
    assert answer['sources']['legal_name']['mark']['state'] == 'check'
    assert answer['status']['legal_name'] == 'to_check'
    assert answer['review'] == {'open': 3, 'check': 1, 'unflagged': 2}
    assert Intake.objects.get(deal=deal).flags == 3


def test_B10_ignore_then_clear_and_revert_once(api, user, deal, read):
    ignored = _marks(api, deal, action='ignore', refs=['intake:atne']).json()
    assert ignored['review']['open'] == 1
    assert _marks(api, deal, action='ignore', refs=['intake:atne']).json()['changed'] == 0  # already so
    activity.revert(ignored['activity_id'], user)
    assert Intake.objects.get(deal=deal).sources['atne'] == DOUBTED
    with pytest.raises(activity.Refused):
        activity.revert(ignored['activity_id'], user)


def test_E88_revert_is_refused_once_the_answer_changed(api, user, deal, read):
    flagged = _marks(api, deal, action='check', refs=['intake:dba']).json()
    services.update_answers(user, deal.id, {'dba': 'Example'})  # a changed value drops its mark
    with pytest.raises(activity.Refused) as refused:
        activity.revert(flagged['activity_id'], user)
    assert 'DBA' in refused.value.sentence


def test_B10_bad_requests_answer_400_and_an_empty_deal_marks_nothing(api, deal):
    assert _marks(api, deal, action='bless').status_code == 400
    assert _marks(api, deal, action='approve', refs=['plan:4:rate_ee']).status_code == 400
    assert _marks(api, deal, action='approve', refs=[]).status_code == 400
    empty = _marks(api, deal, action='approve').json()
    assert empty['changed'] == 0 and empty['activity_id'] is None
    assert not Intake.objects.filter(deal=deal).exists()
