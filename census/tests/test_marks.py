"""Review marks on census cells (plan.md §7.7, §10.7; C3, C8, E85–E88, OQ28): ☑ Select cells marks exactly the picked
cells, the review bar every open warning; a blank takes no mark; the marks (never the values) are recorded and Revert
puts them back; the page draws each cell's review state."""

import pytest

from census import services
from census.models import Member
from conftest import make_deal, write_path_contract
from deals import activity, values

from .helpers import family, imported, roster, xlsx

pytestmark = pytest.mark.django_db

SMITH = family('E1', 'Smith', tier='ES', deps=[('Spouse', 'Blake', '02/02/1981')])


@pytest.fixture
def world(user):
    deal = make_deal(user, requested_lines=('medical',))
    imported(user, deal, xlsx(roster(SMITH)))
    avery = Member.objects.get(deal=deal, kind='employee')
    return {'deal': deal, 'avery': avery}


def doubted(member, key):
    """A value Claude read and doubted (OQ28): the census's AI reads arrive in slice 51; here it is set by hand."""
    entry = values.source('ai', None, low='mapping')
    Member.all_objects.filter(pk=member.id).update(sources={**member.sources, key: entry})
    member.refresh_from_db()


def test_Q3_1_C8_a_mark_is_recorded_and_reverted(user, world):
    avery = world['avery']
    ref = f'census:{avery.id}:last_name'
    row = write_path_contract(
        user,
        avery,
        lambda: services.mark_values(user, world['deal'].id, 'check', refs=[ref]),
        lambda member: member.sources['last_name'].get('mark', {}).get('state'),
        lambda: services.mark_values(user, world['deal'].id, 'ignore', refs=[ref]),
    )
    assert row.summary == 'Flagged 1 census value as needing checking'
    assert list(row.changes[0]['k']) == ['mark.last_name']
    assert 'Smith' not in str(row.changes)  # marks, never the value


def test_C8_OQ28_the_review_bar_marks_every_open_warning_and_nothing_else(user, api, world):
    deal, avery = world['deal'], world['avery']
    doubted(avery, 'medical_plan')
    page = api.get(f'/api/deals/{deal.id}/census/').json()
    assert page['review'] == {'open': 1, 'check': 0, 'unflagged': 1}
    shown = next(member for member in page['members'] if member['id'] == avery.id)
    assert shown['review'] == {'medical_plan': 'to_check'}
    answer = api.post(f'/api/deals/{deal.id}/census/marks/', {'action': 'approve'}, format='json').json()
    assert answer['changed'] == 1
    assert answer['cells'] == [{'ref': f'census:{avery.id}:medical_plan', 'review': 'approved'}]
    assert answer['review'] == {'open': 0, 'check': 0, 'unflagged': 0}
    avery.refresh_from_db()
    assert avery.sources['medical_plan']['confirmed']['by'] == user.id
    assert 'confirmed' not in avery.sources['first_name']  # a clean value was not touched


def test_C8_a_blank_takes_no_mark_and_foreign_cells_are_refused(user, api, world):
    deal, avery = world['deal'], world['avery']
    url = f'/api/deals/{deal.id}/census/marks/'
    blank = api.post(url, {'action': 'check', 'refs': [f'census:{avery.id}:ssn']}, format='json').json()
    assert (blank['changed'], blank['activity_id']) == (0, None)
    other = make_deal(user, name='Other Co (synthetic)')
    imported(user, other, xlsx(roster(family('X1', 'Other'))))
    stranger = Member.objects.get(deal=other)
    assert (
        api.post(url, {'action': 'check', 'refs': [f'census:{stranger.id}:last_name']}, format='json').status_code
        == 400
    )
    assert api.post(url, {'action': 'check', 'refs': ['census:x:last_name']}, format='json').status_code == 400
    assert api.post(url, {'action': 'check', 'refs': [f'census:{avery.id}:nope']}, format='json').status_code == 400
    assert api.post(url, {'action': 'bless'}, format='json').status_code == 400


def test_E88_revert_after_the_value_changed_is_refused_naming_the_column(user, world):
    deal, avery = world['deal'], world['avery']
    marked = services.mark_values(user, deal.id, 'check', refs=[f'census:{avery.id}:last_name'])
    services.edit_values(user, avery.id, {'last_name': 'Smyth'})  # a new value drops its mark (O.6 #35)
    with pytest.raises(activity.Refused) as refused:
        activity.revert(marked.row.id, user)
    assert refused.value.sentence == 'Last Name was changed after this, so this change cannot be reverted.'


def test_C3_a_flagged_cell_shows_check_and_a_cleared_one_nothing(user, api, world):
    deal, avery = world['deal'], world['avery']
    ref = f'census:{avery.id}:dob'
    services.mark_values(user, deal.id, 'check', refs=[ref])
    shown = lambda: next(  # noqa: E731
        m for m in api.get(f'/api/deals/{deal.id}/census/').json()['members'] if m['id'] == avery.id
    )['review']
    assert shown() == {'dob': 'check'}
    services.mark_values(user, deal.id, 'clear')
    assert shown() == {}
